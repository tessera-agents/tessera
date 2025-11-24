"""
LangGraph-based Interviewer Agent implementation.

Provides state persistence and checkpointing for interview workflows.
"""

from datetime import UTC, datetime
from typing import Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from .config import INTERVIEWER_PROMPT, FrameworkConfig
from .graph_base import get_checkpointer
from .interviewer import InterviewerAgent  # For utility methods
from .llm import create_llm

# Scoring thresholds
STRONG_HIRE_THRESHOLD = 80
HIRE_THRESHOLD = 60
MAYBE_THRESHOLD = 40


class InterviewerState(TypedDict):
    """State schema for InterviewerGraph."""

    # Input
    task_description: str
    candidate_name: str | None
    thread_id: str | None

    # Questions
    questions: list[dict] | None

    # Responses
    responses: list[dict] | None

    # Scoring
    scores: list[dict] | None
    overall_score: float | None

    # Final output
    recommendation: dict | None

    # Control flow
    next_action: Literal["ask_questions", "score", "recommend", "end"] | None


class InterviewerGraph:
    """
    LangGraph-based interviewer agent with state persistence.

    Provides interview workflows with:
    - SQLite checkpointing
    - Resume capability
    - Streaming support

    Example:
        >>> from tessera.interviewer_graph import InterviewerGraph
        >>> from tessera.graph_base import get_thread_config
        >>>
        >>> interviewer = InterviewerGraph()
        >>> config = get_thread_config("interview-123")
        >>> result = interviewer.invoke({
        >>>     "task_description": "Build a caching system",
        >>>     "candidate_name": "gpt-4"
        >>> }, config=config)
    """

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        config: FrameworkConfig | None = None,
        system_prompt: str = INTERVIEWER_PROMPT,
    ) -> None:
        """
        Initialize the interviewer graph.

        Args:
            llm: Language model to use
            config: Framework configuration
            system_prompt: Custom system prompt
        """
        self.config = config or FrameworkConfig.from_env()
        self.llm = llm or create_llm(self.config.llm)
        self.system_prompt = system_prompt
        self.scoring_weights = self.config.scoring_weights.normalize()

        # Build the graph
        self.app = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph."""
        workflow = StateGraph(InterviewerState)

        # Add nodes
        workflow.add_node("design", self._design_node)
        workflow.add_node("interview", self._interview_node)
        workflow.add_node("score", self._score_node)
        workflow.add_node("recommend", self._recommend_node)

        # Set entry point
        workflow.set_entry_point("design")

        # Add edges
        workflow.add_edge("design", "interview")
        workflow.add_edge("interview", "score")
        workflow.add_edge("score", "recommend")
        workflow.add_edge("recommend", END)

        # Compile with checkpointer
        checkpointer = get_checkpointer()
        return workflow.compile(checkpointer=checkpointer)

    def _design_node(self, state: InterviewerState) -> InterviewerState:
        """Design interview questions."""
        task_description = state["task_description"]

        prompt = f"""
Task: {task_description}

Design 6 interview questions to evaluate candidates for this task.
Include:
- Representative sample tasks
- Edge-case variations
- Meta-questions about limitations

Respond in JSON format:
{{
    "questions": [
        {{
            "question_id": "Q1",
            "text": "question text",
            "type": "sample/edge-case/meta",
            "evaluation_focus": "what this tests"
        }}
    ]
}}
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        result = InterviewerAgent._parse_json_response(None, response.content)

        return {
            **state,
            "questions": result.get("questions", []),
            "next_action": "ask_questions",
        }

    def _interview_node(self, state: InterviewerState) -> InterviewerState:
        """Simulate candidate responses (in real use, this would query actual candidates)."""
        questions = state.get("questions", [])
        state.get("candidate_name", "unknown")

        # For now, simulate responses
        # In real implementation, this would invoke candidate LLM
        responses = [
            {
                "question_id": q.get("question_id"),
                "question_text": q.get("text"),
                "answer": f"Simulated response to: {q.get('text')[:50]}...",
                "timestamp": datetime.now(UTC).isoformat(),
            }
            for q in questions
        ]

        return {
            **state,
            "responses": responses,
            "next_action": "score",
        }

    def _score_node(self, state: InterviewerState) -> InterviewerState:
        """Score candidate responses."""
        responses = state.get("responses", [])
        state.get("questions", [])

        scores = []
        for resp in responses:
            # Ask LLM to score this response
            prompt = f"""
Score this response on a scale of 0-5 for each metric:

Question: {resp["question_text"]}
Answer: {resp["answer"]}

Provide scores for:
- accuracy (correctness and precision)
- relevance (alignment with question)
- completeness (thoroughness)
- explainability (clarity)
- efficiency (resource awareness)
- safety (risk mitigation)

Respond in JSON format:
{{
    "accuracy": 0-5,
    "relevance": 0-5,
    "completeness": 0-5,
    "explainability": 0-5,
    "efficiency": 0-5,
    "safety": 0-5,
    "rationale": "explanation"
}}
"""

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt),
            ]

            response = self.llm.invoke(messages)
            score_data = InterviewerAgent._parse_json_response(None, response.content)

            scores.append(
                {
                    "question_id": resp["question_id"],
                    "metrics": score_data,
                }
            )

        # Calculate overall weighted score
        if scores:
            avg_metrics = {
                "accuracy": sum(s["metrics"].get("accuracy", 0) for s in scores) / len(scores),
                "relevance": sum(s["metrics"].get("relevance", 0) for s in scores) / len(scores),
                "completeness": sum(s["metrics"].get("completeness", 0) for s in scores) / len(scores),
                "explainability": sum(s["metrics"].get("explainability", 0) for s in scores) / len(scores),
                "efficiency": sum(s["metrics"].get("efficiency", 0) for s in scores) / len(scores),
                "safety": sum(s["metrics"].get("safety", 0) for s in scores) / len(scores),
            }

            # Calculate weighted score
            overall = (
                (
                    avg_metrics["accuracy"] * self.scoring_weights.accuracy
                    + avg_metrics["relevance"] * self.scoring_weights.relevance
                    + avg_metrics["completeness"] * self.scoring_weights.completeness
                    + avg_metrics["explainability"] * self.scoring_weights.explainability
                    + avg_metrics["efficiency"] * self.scoring_weights.efficiency
                    + avg_metrics["safety"] * self.scoring_weights.safety
                )
                / 5.0
                * 100
            )  # Convert to percentage
        else:
            overall = 0.0

        return {
            **state,
            "scores": scores,
            "overall_score": overall,
            "next_action": "recommend",
        }

    def _recommend_node(self, state: InterviewerState) -> InterviewerState:
        """Generate final recommendation."""
        overall_score = state.get("overall_score", 0.0)
        candidate_name = state.get("candidate_name", "unknown")

        # Generate recommendation based on score
        if overall_score >= STRONG_HIRE_THRESHOLD:
            decision = "STRONG HIRE"
        elif overall_score >= HIRE_THRESHOLD:
            decision = "HIRE"
        elif overall_score >= MAYBE_THRESHOLD:
            decision = "MAYBE"
        else:
            decision = "NO HIRE"

        recommendation = {
            "candidate": candidate_name,
            "overall_score": overall_score,
            "decision": decision,
            "rationale": f"Candidate scored {overall_score:.1f}% overall",
        }

        return {
            **state,
            "recommendation": recommendation,
            "next_action": "end",
        }

    def invoke(self, input_data: dict | None, config: dict | None = None) -> dict:
        """
        Invoke the interviewer graph.

        Args:
            input_data: Input state
            config: Configuration including thread_id

        Returns:
            Final state after execution
        """
        return self.app.invoke(input_data, config=config)

    def stream(self, input_data: dict, config: dict | None = None) -> object:
        """
        Stream interviewer graph execution.

        Args:
            input_data: Input state
            config: Configuration including thread_id

        Yields:
            State updates as they occur
        """
        return self.app.stream(input_data, config=config)

    def get_state(self, config: dict) -> dict:
        """
        Get current state from checkpoint.

        Args:
            config: Configuration with thread_id

        Returns:
            Current state
        """
        return self.app.get_state(config)
