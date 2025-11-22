"""
Interviewer agent implementation.
"""

import json
from datetime import datetime
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from .config import INTERVIEWER_PROMPT, FrameworkConfig
from .llm import create_llm
from .models import (
    InterviewResult,
    QuestionResponse,
    Score,
    ScoreMetrics,
)


class InterviewerAgent:
    """
    Interviewer agent that evaluates and selects agents/models for tasks.

    The interviewer designs questions, runs structured interviews,
    scores candidates, and makes recommendations.
    """

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        config: FrameworkConfig | None = None,
        system_prompt: str = INTERVIEWER_PROMPT,
    ) -> None:
        """
        Initialize the interviewer agent.

        Args:
            llm: Language model to use (creates default if None)
            config: Framework configuration
            system_prompt: Custom system prompt (uses default if not provided)
        """
        self.config = config or FrameworkConfig.from_env()
        self.llm = llm or create_llm(self.config.llm)
        self.system_prompt = system_prompt
        self.scoring_weights = self.config.scoring_weights.normalize()

    def design_interview(
        self, task_description: str, num_questions: int = 6
    ) -> list[dict[str, str]]:
        """
        Design interview questions for a task.

        Args:
            task_description: Description of the task to evaluate for
            num_questions: Number of questions to generate

        Returns:
            List of interview questions
        """
        prompt = f"""
Task: {task_description}

Design {num_questions} interview questions to evaluate candidates for this task.
Include:
- Representative sample tasks (same for all candidates)
- Edge-case variations to test robustness
- Meta-questions about limitations

Respond in JSON format:
{{
    "questions": [
        {{
            "question_id": "Q1",
            "text": "question text",
            "type": "sample/edge-case/meta",
            "evaluation_focus": "what this question tests"
        }}
    ]
}}
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        result = self._parse_json_response(response.content)
        return result.get("questions", [])

    def conduct_interview(
        self,
        candidate_name: str,
        candidate_llm: BaseChatModel,
        questions: list[dict[str, str]],
        task_description: str,
    ) -> InterviewResult:
        """
        Conduct an interview with a candidate agent.

        Args:
            candidate_name: Name of the candidate
            candidate_llm: LLM instance for the candidate
            questions: List of interview questions
            task_description: Task description for context

        Returns:
            Interview result with responses and scores
        """
        responses: list[QuestionResponse] = []

        # Ask each question
        for q in questions:
            prompt = f"""
Task Context: {task_description}

Question: {q["text"]}

Please provide a detailed answer.
"""
            candidate_response = candidate_llm.invoke([HumanMessage(content=prompt)])

            responses.append(
                QuestionResponse(
                    question_id=q["question_id"],
                    question_text=q["text"],
                    answer=candidate_response.content,
                )
            )

        # Score the responses
        scores = self._score_responses(candidate_name, questions, responses, task_description)

        # Calculate aggregated score
        aggregated_score = sum(s.overall_score for s in scores) / len(scores) if scores else 0.0

        # Generate recommendation
        recommendation = self._generate_recommendation(
            candidate_name, aggregated_score, responses, scores
        )

        return InterviewResult(
            candidate=candidate_name,
            questions=responses,
            scores=scores,
            aggregated_score=aggregated_score,
            recommendation=recommendation["recommendation"],
            weaknesses=recommendation.get("weaknesses", []),
            guardrails=recommendation.get("guardrails", []),
            transcript={
                "task_description": task_description,
                "questions": list(questions),
                "timestamp": datetime.now().isoformat(),
            },
        )

    def compare_candidates(self, results: list[InterviewResult]) -> dict[str, Any]:
        """
        Compare multiple interview results and rank candidates.

        Args:
            results: List of interview results for different candidates

        Returns:
            Comparison with rankings and recommendation
        """
        if not results:
            return {"error": "No results to compare"}

        # Sort by aggregated score
        sorted_results = sorted(results, key=lambda r: r.aggregated_score, reverse=True)

        # Assign rankings
        for i, result in enumerate(sorted_results, 1):
            result.ranking = i

        prompt = f"""
Compare these interview results and provide a final recommendation:

{self._format_results_for_comparison(sorted_results)}

Provide:
1. Justification for the top candidate with specific evidence
2. Key differentiators between top candidates
3. Confidence level (High/Medium/Low)

Respond in JSON format:
{{
    "selected_candidate": "name",
    "justification": "detailed reasoning with evidence",
    "key_differentiators": ["point 1", "point 2"],
    "confidence": "High/Medium/Low",
    "runner_up": "name"
}}
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        comparison = self._parse_json_response(response.content)

        return {
            "rankings": [
                {"candidate": r.candidate, "score": r.aggregated_score, "rank": r.ranking}
                for r in sorted_results
            ],
            "selected_candidate": comparison.get("selected_candidate", sorted_results[0].candidate),
            "justification": comparison.get("justification", ""),
            "confidence": comparison.get("confidence", "Medium"),
            "runner_up": comparison.get(
                "runner_up", sorted_results[1].candidate if len(sorted_results) > 1 else None
            ),
            "key_differentiators": comparison.get("key_differentiators", []),
        }

    def break_tie(
        self,
        tied_candidates: list[str],
        candidate_llms: dict[str, BaseChatModel],
        task_description: str,
    ) -> dict[str, Any]:
        """
        Break a tie between candidates using a tie-breaker question.

        Args:
            tied_candidates: Names of tied candidates
            candidate_llms: Mapping of candidate names to LLM instances
            task_description: Task description

        Returns:
            Tie-breaker decision
        """
        # Design a harder variant question
        prompt = f"""
Task: {task_description}

Design ONE challenging tie-breaker question that will help differentiate between equally-qualified candidates.
Make it a harder variant that tests deeper capability.

Respond in JSON format:
{{
    "question": "the tie-breaker question",
    "evaluation_focus": "what this specifically tests"
}}
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        tiebreaker = self._parse_json_response(response.content)

        # Ask all tied candidates
        responses: dict[str, str] = {}
        for candidate in tied_candidates:
            if candidate not in candidate_llms:
                continue

            candidate_response = candidate_llms[candidate].invoke(
                [HumanMessage(content=tiebreaker["question"])]
            )
            responses[candidate] = candidate_response.content

        # Evaluate responses
        evaluation_prompt = f"""
Tie-breaker question: {tiebreaker["question"]}

Candidate responses:
{chr(10).join(f"{name}: {resp}" for name, resp in responses.items())}

Evaluate and select the best candidate. Provide specific justification.

Respond in JSON format:
{{
    "selected_candidate": "name",
    "justification": "specific advantage that broke the tie",
    "scores": {{"candidate_name": score_0_to_100}}
}}
"""

        eval_messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=evaluation_prompt),
        ]

        eval_response = self.llm.invoke(eval_messages)
        decision = self._parse_json_response(eval_response.content)

        return {
            "tiebreaker_question": tiebreaker["question"],
            "responses": responses,
            "selected_candidate": decision.get("selected_candidate"),
            "justification": decision.get("justification"),
            "scores": decision.get("scores", {}),
            "timestamp": datetime.now().isoformat(),
        }

    def _score_responses(
        self,
        candidate_name: str,
        questions: list[dict[str, str]],
        responses: list[QuestionResponse],
        task_description: str,
    ) -> list[Score]:
        """Score candidate responses."""
        scores: list[Score] = []

        for q, r in zip(questions, responses, strict=False):
            score_prompt = f"""
Task: {task_description}

Question: {q["text"]}
Type: {q.get("type", "general")}

Candidate Answer: {r.answer}

Score this answer on each metric (0-5 scale):
- Accuracy: correctness and precision
- Relevance: how well it addresses the question
- Completeness: thoroughness of the answer
- Explainability: clarity and understandability
- Efficiency: conciseness and resource awareness
- Safety: awareness of risks and ethical concerns

Respond in JSON format:
{{
    "metrics": {{
        "accuracy": 0-5,
        "relevance": 0-5,
        "completeness": 0-5,
        "explainability": 0-5,
        "efficiency": 0-5,
        "safety": 0-5
    }},
    "rationale": "1-3 sentence justification with evidence"
}}
"""

            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=score_prompt),
            ]

            score_response = self.llm.invoke(messages)
            score_data = self._parse_json_response(score_response.content)

            metrics = ScoreMetrics(**score_data["metrics"])
            overall = self._calculate_weighted_score(metrics)

            scores.append(
                Score(
                    question_id=q["question_id"],
                    candidate=candidate_name,
                    panelist="interviewer",
                    metrics=metrics,
                    rationale=score_data.get("rationale", ""),
                    overall_score=overall,
                )
            )

        return scores

    def _calculate_weighted_score(self, metrics: ScoreMetrics) -> float:
        """Calculate weighted overall score from metrics."""
        weights = self.scoring_weights

        # Normalize each metric to 0-1
        normalized = {
            "accuracy": metrics.accuracy / 5.0,
            "relevance": metrics.relevance / 5.0,
            "completeness": metrics.completeness / 5.0,
            "explainability": metrics.explainability / 5.0,
            "efficiency": metrics.efficiency / 5.0,
            "safety": metrics.safety / 5.0,
        }

        # Calculate weighted sum
        weighted_sum = (
            weights.accuracy * normalized["accuracy"]
            + weights.relevance * normalized["relevance"]
            + weights.completeness * normalized["completeness"]
            + weights.explainability * normalized["explainability"]
            + weights.efficiency * normalized["efficiency"]
            + weights.safety * normalized["safety"]
        )

        return round(weighted_sum * 100, 2)

    def _generate_recommendation(
        self,
        candidate_name: str,
        aggregated_score: float,
        responses: list[QuestionResponse],
        scores: list[Score],
    ) -> dict[str, Any]:
        """Generate recommendation based on interview results."""
        prompt = f"""
Candidate: {candidate_name}
Aggregated Score: {aggregated_score}/100

Scores by question:
{chr(10).join(f"- {s.question_id}: {s.overall_score}/100 - {s.rationale}" for s in scores)}

Based on these results, provide:
1. Overall recommendation (approve/conditional/reject)
2. Key weaknesses to be aware of
3. Suggested guardrails for deployment (monitoring, checks, etc.)

Respond in JSON format:
{{
    "recommendation": "approve/conditional/reject with brief reasoning",
    "weaknesses": ["weakness 1", "weakness 2"],
    "guardrails": ["guardrail 1", "guardrail 2"]
}}
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        return self._parse_json_response(response.content)

    def _format_results_for_comparison(self, results: list[InterviewResult]) -> str:
        """Format interview results for comparison."""
        formatted = []
        for r in results:
            formatted.append(
                f"""
Candidate: {r.candidate}
Aggregated Score: {r.aggregated_score}/100
Recommendation: {r.recommendation}
Weaknesses: {", ".join(r.weaknesses) if r.weaknesses else "None noted"}
"""
            )
        return "\n".join(formatted)

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        content = content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            import re

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Failed to parse JSON response: {e}")
