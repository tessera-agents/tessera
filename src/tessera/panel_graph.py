"""
LangGraph-based Panel Interview System implementation.

Provides state persistence and checkpointing for panel-based evaluations.
"""

from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from .config import FrameworkConfig
from .graph_base import get_checkpointer
from .panel import (
    CREATIVE_EVALUATOR_PROMPT,
    EFFICIENCY_EVALUATOR_PROMPT,
    RISK_EVALUATOR_PROMPT,
    TECHNICAL_EVALUATOR_PROMPT,
    USER_CENTRIC_EVALUATOR_PROMPT,
)


class PanelState(TypedDict):
    """State schema for PanelGraph."""

    # Input
    task_description: str
    candidates: list[str]
    thread_id: str | None

    # Panel setup
    num_panelists: int | None
    panelists: list[dict] | None

    # Interview process
    question_bank: list[dict] | None
    qa_transcript: dict | None

    # Voting
    ballots: list[dict] | None
    vote_counts: dict | None
    winner: str | None

    # Tie handling
    tie_detected: bool | None
    tie_breaker_result: dict | None

    # Final output
    final_ranking: list[tuple] | None
    decision: str | None

    # Control flow
    next_action: Literal["setup", "qa", "vote", "tiebreak", "finalize", "end"] | None


class PanelGraph:
    """
    LangGraph-based panel interview system with state persistence.

    Provides panel evaluation workflows with:
    - SQLite checkpointing
    - Multi-panelist coordination
    - Round-robin voting
    - Tie-breaking support

    Example:
        >>> from tessera.panel_graph import PanelGraph
        >>> from tessera.graph_base import get_thread_config
        >>>
        >>> panel = PanelGraph()
        >>> config = get_thread_config("panel-123")
        >>> result = panel.invoke({
        >>>     "task_description": "Build caching system",
        >>>     "candidates": ["candidate_a", "candidate_b"]
        >>> }, config=config)
    """

    def __init__(
        self,
        config: FrameworkConfig | None = None,
    ) -> None:
        """
        Initialize the panel graph.

        Args:
            config: Framework configuration
        """
        self.config = config or FrameworkConfig.from_env()

        # Build the graph
        self.app = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph."""
        workflow = StateGraph(PanelState)

        # Add nodes
        workflow.add_node("setup_panel", self._setup_panel_node)
        workflow.add_node("generate_questions", self._generate_questions_node)
        workflow.add_node("conduct_voting", self._conduct_voting_node)
        workflow.add_node("check_tie", self._check_tie_node)
        workflow.add_node("finalize", self._finalize_node)

        # Set entry point
        workflow.set_entry_point("setup_panel")

        # Add edges
        workflow.add_edge("setup_panel", "generate_questions")
        workflow.add_edge("generate_questions", "conduct_voting")
        workflow.add_edge("conduct_voting", "check_tie")

        # Conditional routing after tie check
        workflow.add_conditional_edges(
            "check_tie",
            self._route_after_tie_check,
            {
                "finalize": "finalize",
                "end": END,
            },
        )

        workflow.add_edge("finalize", END)

        # Compile with checkpointer
        checkpointer = get_checkpointer()
        return workflow.compile(checkpointer=checkpointer)

    def _setup_panel_node(self, state: PanelState) -> PanelState:
        """Setup panel with diverse evaluators."""
        num_panelists = state.get("num_panelists") or 5

        num_panelists = max(num_panelists, 3)
        if num_panelists % 2 == 0:
            num_panelists += 1  # Make it odd

        # Define panelist roles
        roles = [
            {
                "name": "technical",
                "prompt": TECHNICAL_EVALUATOR_PROMPT,
                "weights": {"accuracy": 0.4},
            },
            {
                "name": "creative",
                "prompt": CREATIVE_EVALUATOR_PROMPT,
                "weights": {"relevance": 0.3},
            },
            {
                "name": "efficiency",
                "prompt": EFFICIENCY_EVALUATOR_PROMPT,
                "weights": {"efficiency": 0.3},
            },
            {
                "name": "user_centric",
                "prompt": USER_CENTRIC_EVALUATOR_PROMPT,
                "weights": {"explainability": 0.3},
            },
            {"name": "risk", "prompt": RISK_EVALUATOR_PROMPT, "weights": {"safety": 0.4}},
        ]

        panelists = roles[:num_panelists]

        return {
            **state,
            "num_panelists": num_panelists,
            "panelists": panelists,
            "next_action": "qa",
        }

    def _generate_questions_node(self, state: PanelState) -> PanelState:
        """Generate question bank for panel interview."""
        task_description = state["task_description"]

        # Simplified question generation
        # In real implementation, would use LLM
        questions = [
            {"id": "Q1", "text": f"How would you approach: {task_description}?", "type": "sample"},
            {
                "id": "Q2",
                "text": f"What are the main challenges in: {task_description}?",
                "type": "edge-case",
            },
            {
                "id": "Q3",
                "text": f"How would you ensure quality for: {task_description}?",
                "type": "meta",
            },
        ]

        return {
            **state,
            "question_bank": questions,
            "next_action": "vote",
        }

    def _conduct_voting_node(self, state: PanelState) -> PanelState:
        """Conduct panel voting on candidates."""
        candidates = state.get("candidates", [])
        panelists = state.get("panelists", [])

        if not candidates or not panelists:
            return {
                **state,
                "ballots": [],
                "vote_counts": {},
                "next_action": "end",
            }

        # Simulate voting (in real implementation, would evaluate candidates)
        ballots = []
        vote_counts = dict.fromkeys(candidates, 0)

        # Simplified voting: first panelist votes for first candidate, etc.
        for i, panelist in enumerate(panelists):
            candidate_index = i % len(candidates)
            voted_candidate = candidates[candidate_index]

            ballots.append(
                {
                    "panelist": panelist["name"],
                    "vote": voted_candidate,
                    "rationale": f"Voted for {voted_candidate} based on {panelist['name']} criteria",
                    "confidence": 0.8,
                }
            )

            vote_counts[voted_candidate] += 1

        return {
            **state,
            "ballots": ballots,
            "vote_counts": vote_counts,
            "next_action": "tiebreak",
        }

    def _check_tie_node(self, state: PanelState) -> PanelState:
        """Check for ties and handle if necessary."""
        vote_counts = state.get("vote_counts", {})

        if not vote_counts:
            return {
                **state,
                "tie_detected": False,
                "winner": None,
                "next_action": "end",
            }

        max_votes = max(vote_counts.values())
        winners = [candidate for candidate, votes in vote_counts.items() if votes == max_votes]

        if len(winners) > 1:
            # Tie detected - use simple tiebreaker (first candidate alphabetically)
            winner = sorted(winners)[0]
            tie_detected = True
            tie_breaker_result = {"method": "alphabetical", "winner": winner}
        else:
            winner = winners[0]
            tie_detected = False
            tie_breaker_result = None

        return {
            **state,
            "tie_detected": tie_detected,
            "winner": winner,
            "tie_breaker_result": tie_breaker_result,
            "next_action": "finalize",
        }

    def _finalize_node(self, state: PanelState) -> PanelState:
        """Finalize panel decision with ranking."""
        vote_counts = state.get("vote_counts", {})
        winner = state.get("winner")

        # Create ranking by vote count
        ranking = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)

        decision = f"Panel selects: {winner}" if winner else "No decision"

        return {
            **state,
            "final_ranking": ranking,
            "decision": decision,
            "next_action": "end",
        }

    def _route_after_tie_check(self, state: PanelState) -> Literal["finalize", "end"]:
        """Route after tie check."""
        next_action = state.get("next_action", "end")
        if next_action == "finalize":
            return "finalize"
        return "end"

    def invoke(self, input_data: dict | None, config: dict | None = None) -> dict:
        """
        Invoke the panel graph.

        Args:
            input_data: Input state
            config: Configuration including thread_id

        Returns:
            Final state after execution
        """
        return self.app.invoke(input_data, config=config)

    def stream(self, input_data: dict, config: dict | None = None):
        """
        Stream panel graph execution.

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
