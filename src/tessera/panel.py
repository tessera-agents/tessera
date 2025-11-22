"""
Panel interview system implementation with round-robin voting.
"""

import json
from datetime import datetime
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from .config import FrameworkConfig
from .interviewer import InterviewerAgent
from .llm import create_llm
from .models import (
    Ballot,
    PanelResult,
    ScoreMetrics,
    Vote,
)

# Panelist role prompts
TECHNICAL_EVALUATOR_PROMPT = """You are a Technical Evaluator in an agent evaluation panel.
Focus on: Correctness, depth, precision, error handling, and technical accuracy."""

CREATIVE_EVALUATOR_PROMPT = """You are a Creative Evaluator in an agent evaluation panel.
Focus on: Originality, engagement, style, innovation, and creative problem-solving."""

EFFICIENCY_EVALUATOR_PROMPT = """You are an Efficiency Evaluator in an agent evaluation panel.
Focus on: Conciseness, speed, resource efficiency, and cost-effectiveness."""

USER_CENTRIC_EVALUATOR_PROMPT = """You are a User-Centric Evaluator in an agent evaluation panel.
Focus on: Clarity, usefulness, accessibility, empathy, and user experience."""

RISK_EVALUATOR_PROMPT = """You are a Risk Evaluator in an agent evaluation panel.
Focus on: Safety, bias detection, failure modes, ethical concerns, and security."""


class PanelistAgent:
    """A panelist that evaluates candidates."""

    def __init__(
        self,
        name: str,
        role: str,
        llm: BaseChatModel,
        system_prompt: str,
        scoring_weights: dict[str, float],
    ) -> None:
        """
        Initialize a panelist.

        Args:
            name: Panelist identifier
            role: Role type (technical, creative, etc.)
            llm: Language model for this panelist
            system_prompt: System prompt for the role
            scoring_weights: Metric weights for this panelist
        """
        self.name = name
        self.role = role
        self.llm = llm
        self.system_prompt = system_prompt
        self.scoring_weights = scoring_weights

    def ask_question(
        self, task_description: str, question_bank: list[dict[str, str]]
    ) -> dict[str, str]:
        """
        Ask a question from the question bank, tailored to this panelist's focus.

        Args:
            task_description: The task being evaluated
            question_bank: Available questions

        Returns:
            Selected question
        """
        # For now, select based on role focus
        # In a real implementation, could use LLM to select/customize
        for q in question_bank:
            if self.role.lower() in q.get("evaluation_focus", "").lower():
                return q

        # Fallback to first question
        return (
            question_bank[0]
            if question_bank
            else {
                "question_id": "Q_default",
                "text": f"How would you approach this task from a {self.role} perspective?",
                "type": "general",
            }
        )

    def score_answer(
        self,
        candidate: str,
        question: dict[str, str],
        answer: str,
        task_description: str,
    ) -> Ballot:
        """
        Score a candidate's answer and cast a ballot.

        Args:
            candidate: Candidate name
            question: The question that was asked
            answer: Candidate's answer
            task_description: Task context

        Returns:
            Ballot with scores and vote
        """
        score_prompt = f"""
Task: {task_description}

Question ({self.role} focus): {question["text"]}

Candidate Answer: {answer}

As a {self.role}, evaluate this answer on all metrics (0-5 scale):
- Accuracy: correctness and precision
- Relevance: how well it addresses the question
- Completeness: thoroughness
- Explainability: clarity
- Efficiency: conciseness and resource awareness
- Safety: awareness of risks

Then provide:
1. Overall assessment (0-100 weighted score)
2. Brief rationale (2-3 sentences with specific evidence)
3. Your vote: HIRE or PASS

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
    "overall_score": 0-100,
    "rationale": "specific evidence-based reasoning",
    "vote": "HIRE or PASS"
}}
"""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=score_prompt),
        ]

        response = self.llm.invoke(messages)
        score_data = self._parse_json_response(response.content)

        metrics = ScoreMetrics(**score_data["metrics"])
        vote_str = score_data.get("vote", "PASS").upper()
        vote = Vote.HIRE if vote_str == "HIRE" else Vote.PASS

        return Ballot(
            candidate=candidate,
            panelist=self.name,
            vote=vote,
            scores=metrics,
            overall_score=score_data.get("overall_score", 0),
            rationale=score_data.get("rationale", ""),
        )

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Parse JSON from LLM response."""
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError("Failed to parse JSON response")


class PanelSystem:
    """
    Panel interview system with round-robin voting.

    Manages multiple panelists who evaluate candidates through
    structured interviews and voting.
    """

    def __init__(
        self,
        config: FrameworkConfig | None = None,
        interviewer: InterviewerAgent | None = None,
    ) -> None:
        """
        Initialize the panel system.

        Args:
            config: Framework configuration
            interviewer: Interviewer agent for tie-breaking
        """
        self.config = config or FrameworkConfig.from_env()
        self.interviewer = interviewer or InterviewerAgent(config=self.config)
        self.panelists: list[PanelistAgent] = []

    def create_default_panel(self, num_panelists: int = 5) -> list[PanelistAgent]:
        """
        Create a default panel with diverse perspectives.

        Args:
            num_panelists: Number of panelists (3-5 recommended, must be odd)

        Returns:
            List of panelist agents
        """
        if num_panelists < 3:
            raise ValueError("Need at least 3 panelists")
        if num_panelists % 2 == 0:
            raise ValueError("Number of panelists should be odd to avoid ties")

        roles = [
            (
                "technical",
                TECHNICAL_EVALUATOR_PROMPT,
                {
                    "accuracy": 0.4,
                    "relevance": 0.2,
                    "completeness": 0.2,
                    "explainability": 0.1,
                    "efficiency": 0.05,
                    "safety": 0.05,
                },
            ),
            (
                "creative",
                CREATIVE_EVALUATOR_PROMPT,
                {
                    "accuracy": 0.1,
                    "relevance": 0.3,
                    "completeness": 0.2,
                    "explainability": 0.2,
                    "efficiency": 0.1,
                    "safety": 0.1,
                },
            ),
            (
                "efficiency",
                EFFICIENCY_EVALUATOR_PROMPT,
                {
                    "accuracy": 0.2,
                    "relevance": 0.2,
                    "completeness": 0.1,
                    "explainability": 0.1,
                    "efficiency": 0.3,
                    "safety": 0.1,
                },
            ),
            (
                "user_centric",
                USER_CENTRIC_EVALUATOR_PROMPT,
                {
                    "accuracy": 0.15,
                    "relevance": 0.25,
                    "completeness": 0.15,
                    "explainability": 0.3,
                    "efficiency": 0.05,
                    "safety": 0.1,
                },
            ),
            (
                "risk",
                RISK_EVALUATOR_PROMPT,
                {
                    "accuracy": 0.15,
                    "relevance": 0.15,
                    "completeness": 0.15,
                    "explainability": 0.1,
                    "efficiency": 0.05,
                    "safety": 0.4,
                },
            ),
        ]

        self.panelists = []
        for i in range(min(num_panelists, len(roles))):
            role_name, prompt, weights = roles[i]
            llm = create_llm(self.config.llm)
            panelist = PanelistAgent(
                name=f"panelist_{role_name}",
                role=role_name,
                llm=llm,
                system_prompt=prompt,
                scoring_weights=weights,
            )
            self.panelists.append(panelist)

        return self.panelists

    def conduct_panel_interview(
        self,
        task_description: str,
        candidates: list[str],
        candidate_llms: dict[str, BaseChatModel],
        question_bank: list[dict[str, str]] | None = None,
    ) -> PanelResult:
        """
        Conduct a full panel interview with round-robin evaluation.

        Args:
            task_description: The task to evaluate for
            candidates: List of candidate names
            candidate_llms: Mapping of candidate names to their LLM instances
            question_bank: Questions to ask (generated if not provided)

        Returns:
            Panel result with votes and decision
        """
        session_id = f"panel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Generate questions if not provided
        if not question_bank:
            question_bank = self.interviewer.design_interview(task_description)

        # Ensure we have panelists
        if not self.panelists:
            self.create_default_panel()

        all_ballots: list[Ballot] = []
        transcript: dict[str, Any] = {
            "session_id": session_id,
            "task": task_description,
            "rounds": [],
        }

        # Round-robin Q&A for each candidate
        for candidate in candidates:
            if candidate not in candidate_llms:
                continue

            candidate_transcript: dict[str, Any] = {
                "candidate": candidate,
                "questions": [],
            }

            # Each panelist asks a question in round-robin
            for _i, panelist in enumerate(self.panelists):
                # Select question for this panelist
                question = panelist.ask_question(task_description, question_bank)

                # Candidate answers
                answer_response = candidate_llms[candidate].invoke(
                    [
                        HumanMessage(
                            content=f"Task: {task_description}\n\nQuestion: {question['text']}"
                        )
                    ]
                )
                answer = answer_response.content

                candidate_transcript["questions"].append(
                    {
                        "panelist": panelist.name,
                        "question": question["text"],
                        "answer": answer,
                    }
                )

                # All panelists score this answer
                for scorer in self.panelists:
                    ballot = scorer.score_answer(
                        candidate=candidate,
                        question=question,
                        answer=answer,
                        task_description=task_description,
                    )
                    all_ballots.append(ballot)

            transcript["rounds"].append(candidate_transcript)

        # Tally votes
        vote_counts: dict[str, dict[str, int]] = {
            candidate: {"HIRE": 0, "PASS": 0} for candidate in candidates
        }

        for ballot in all_ballots:
            if ballot.vote == Vote.HIRE:
                vote_counts[ballot.candidate]["HIRE"] += 1
            else:
                vote_counts[ballot.candidate]["PASS"] += 1

        # Calculate average scores and rank candidates
        candidate_scores: dict[str, float] = {}
        for candidate in candidates:
            candidate_ballots = [b for b in all_ballots if b.candidate == candidate]
            if candidate_ballots:
                avg_score = sum(b.overall_score for b in candidate_ballots) / len(candidate_ballots)
                candidate_scores[candidate] = avg_score
            else:
                candidate_scores[candidate] = 0.0

        final_ranking = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)

        # Determine decision
        decision = None
        confidence = "medium"
        tie_breaker_used = False

        # Check for majority hire vote
        for candidate in candidates:
            hire_votes = vote_counts[candidate]["HIRE"]
            total_votes = len(self.panelists)

            if hire_votes > total_votes / 2:
                decision = candidate
                if hire_votes >= total_votes * 0.8:
                    confidence = "high"
                break

        # Handle ties
        if not decision and len(candidates) > 1:
            # Use interviewer as tie-breaker
            top_candidates = [c for c, _ in final_ranking[:2]]
            tie_break_result = self.interviewer.break_tie(
                tied_candidates=top_candidates,
                candidate_llms=candidate_llms,
                task_description=task_description,
            )
            decision = tie_break_result["selected_candidate"]
            tie_breaker_used = True
            confidence = "low"
            transcript["tie_breaker"] = tie_break_result

        return PanelResult(
            session_id=session_id,
            task_description=task_description,
            candidates=candidates,
            panelists=[p.name for p in self.panelists],
            ballots=all_ballots,
            final_ranking=final_ranking,
            decision=decision,
            confidence=confidence,
            tie_breaker_used=tie_breaker_used,
            transcript=transcript,
        )

    def get_vote_summary(self, result: PanelResult) -> dict[str, Any]:
        """
        Get a summary of the voting results.

        Args:
            result: Panel result

        Returns:
            Vote summary
        """
        vote_counts: dict[str, dict[str, int]] = {
            candidate: {"HIRE": 0, "PASS": 0} for candidate in result.candidates
        }

        for ballot in result.ballots:
            if ballot.vote == Vote.HIRE:
                vote_counts[ballot.candidate]["HIRE"] += 1
            else:
                vote_counts[ballot.candidate]["PASS"] += 1

        return {
            "session_id": result.session_id,
            "vote_counts": vote_counts,
            "final_ranking": result.final_ranking,
            "decision": result.decision,
            "confidence": result.confidence,
            "tie_breaker_used": result.tie_breaker_used,
        }
