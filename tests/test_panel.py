"""Unit tests for Panel system."""

import pytest

from tessera.interviewer import InterviewerAgent
from tessera.models import ScoreMetrics, Vote
from tessera.panel import PanelistAgent, PanelSystem


@pytest.mark.unit
class TestPanelistAgent:
    """Test Panelist agent functionality."""

    def test_panelist_initialization(self, mock_llm):
        """Test panelist initialization."""
        panelist = PanelistAgent(
            name="test_panelist",
            role="technical",
            llm=mock_llm,
            system_prompt="Test prompt",
            scoring_weights={"accuracy": 0.5, "safety": 0.5},
        )

        assert panelist.name == "test_panelist"
        assert panelist.role == "technical"
        assert panelist.llm == mock_llm
        assert panelist.scoring_weights["accuracy"] == 0.5

    def test_ask_question(self, mock_llm, sample_questions):
        """Test asking a question."""
        panelist = PanelistAgent(
            name="technical_panelist",
            role="technical",
            llm=mock_llm,
            system_prompt="Test",
            scoring_weights={},
        )

        question = panelist.ask_question(
            task_description="Test task",
            question_bank=sample_questions,
        )

        assert "question_id" in question
        assert "text" in question

    def test_score_answer(self, mock_llm_with_response, sample_ballot_response):
        """Test scoring an answer."""
        llm = mock_llm_with_response(sample_ballot_response)

        panelist = PanelistAgent(
            name="test_panelist",
            role="technical",
            llm=llm,
            system_prompt="Test",
            scoring_weights={},
        )

        question = {
            "question_id": "Q1",
            "text": "Test question",
            "type": "sample",
        }

        ballot = panelist.score_answer(
            candidate="TestCandidate",
            question=question,
            answer="Test answer",
            task_description="Test task",
        )

        assert ballot.candidate == "TestCandidate"
        assert ballot.panelist == "test_panelist"
        assert ballot.vote in [Vote.HIRE, Vote.PASS]
        assert 0 <= ballot.overall_score <= 100


@pytest.mark.unit
class TestPanelSystem:
    """Test Panel system functionality."""

    def test_panel_initialization(self, test_config):
        """Test panel initialization."""
        panel = PanelSystem(config=test_config)

        assert panel.config == test_config
        assert isinstance(panel.interviewer, InterviewerAgent)
        assert len(panel.panelists) == 0

    def test_create_default_panel(self, test_config):
        """Test creating default panel."""
        panel = PanelSystem(config=test_config)

        panelists = panel.create_default_panel(num_panelists=5)

        assert len(panelists) == 5
        assert len(panel.panelists) == 5
        assert all(isinstance(p, PanelistAgent) for p in panelists)

        # Check diversity of roles
        roles = [p.role for p in panelists]
        assert len(set(roles)) == 5  # All different roles

    def test_create_default_panel_requires_odd_number(self, test_config):
        """Test that panel requires odd number of panelists."""
        panel = PanelSystem(config=test_config)

        with pytest.raises(ValueError, match="should be odd"):
            panel.create_default_panel(num_panelists=4)

    def test_create_default_panel_requires_minimum(self, test_config):
        """Test that panel requires at least 3 panelists."""
        panel = PanelSystem(config=test_config)

        with pytest.raises(ValueError, match="at least 3"):
            panel.create_default_panel(num_panelists=1)

    def test_create_default_panel_three_panelists(self, test_config):
        """Test creating panel with 3 panelists."""
        panel = PanelSystem(config=test_config)

        panelists = panel.create_default_panel(num_panelists=3)

        assert len(panelists) == 3

    def test_conduct_panel_interview(
        self, mock_llm_with_response, test_config, sample_ballot_response
    ):
        """Test conducting a panel interview."""
        panel = PanelSystem(config=test_config)

        # Create small panel
        panel.create_default_panel(num_panelists=3)

        # Mock panelist LLMs to return ballots
        for panelist in panel.panelists:
            panelist.llm = mock_llm_with_response(sample_ballot_response)

        # Mock interviewer for question design
        questions_response = """
        {
            "questions": [
                {
                    "question_id": "Q1",
                    "text": "Test question",
                    "type": "sample",
                    "evaluation_focus": "general"
                }
            ]
        }
        """
        panel.interviewer.llm = mock_llm_with_response(questions_response)

        # Create candidate LLMs
        candidate_llms = {
            "CandidateA": mock_llm_with_response("Answer A"),
            "CandidateB": mock_llm_with_response("Answer B"),
        }

        # Conduct interview
        result = panel.conduct_panel_interview(
            task_description="Test task",
            candidates=["CandidateA", "CandidateB"],
            candidate_llms=candidate_llms,
        )

        assert result.session_id.startswith("panel_")
        assert len(result.candidates) == 2
        assert len(result.panelists) == 3
        assert len(result.ballots) > 0
        assert len(result.final_ranking) == 2
        assert result.decision in ["CandidateA", "CandidateB", None]

    def test_conduct_panel_interview_with_question_bank(
        self, mock_llm_with_response, test_config, sample_questions, sample_ballot_response
    ):
        """Test panel interview with provided question bank."""
        panel = PanelSystem(config=test_config)
        panel.create_default_panel(num_panelists=3)

        # Mock panelists
        for panelist in panel.panelists:
            panelist.llm = mock_llm_with_response(sample_ballot_response)

        # Candidate LLMs
        candidate_llms = {
            "CandidateA": mock_llm_with_response("Answer A"),
        }

        result = panel.conduct_panel_interview(
            task_description="Test task",
            candidates=["CandidateA"],
            candidate_llms=candidate_llms,
            question_bank=sample_questions,
        )

        assert result is not None
        assert len(result.candidates) == 1

    def test_get_vote_summary(self, test_config):
        """Test getting vote summary."""
        from tessera.models import Ballot, PanelResult

        panel = PanelSystem(config=test_config)

        # Create mock panel result
        ballots = [
            Ballot(
                candidate="CandidateA",
                panelist="P1",
                vote=Vote.HIRE,
                scores=ScoreMetrics(
                    accuracy=4.0,
                    relevance=4.0,
                    completeness=4.0,
                    explainability=4.0,
                    efficiency=4.0,
                    safety=4.0,
                ),
                overall_score=80.0,
                rationale="Good",
            ),
            Ballot(
                candidate="CandidateA",
                panelist="P2",
                vote=Vote.PASS,
                scores=ScoreMetrics(
                    accuracy=3.0,
                    relevance=3.0,
                    completeness=3.0,
                    explainability=3.0,
                    efficiency=3.0,
                    safety=3.0,
                ),
                overall_score=60.0,
                rationale="Okay",
            ),
            Ballot(
                candidate="CandidateB",
                panelist="P1",
                vote=Vote.HIRE,
                scores=ScoreMetrics(
                    accuracy=5.0,
                    relevance=5.0,
                    completeness=5.0,
                    explainability=5.0,
                    efficiency=5.0,
                    safety=5.0,
                ),
                overall_score=100.0,
                rationale="Excellent",
            ),
        ]

        result = PanelResult(
            session_id="test_session",
            task_description="Test",
            candidates=["CandidateA", "CandidateB"],
            panelists=["P1", "P2"],
            ballots=ballots,
            final_ranking=[("CandidateB", 100.0), ("CandidateA", 70.0)],
            decision="CandidateB",
            confidence="high",
        )

        summary = panel.get_vote_summary(result)

        assert summary["session_id"] == "test_session"
        assert summary["decision"] == "CandidateB"
        assert summary["vote_counts"]["CandidateA"]["HIRE"] == 1
        assert summary["vote_counts"]["CandidateA"]["PASS"] == 1
        assert summary["vote_counts"]["CandidateB"]["HIRE"] == 1


@pytest.mark.unit
class TestPanelRoles:
    """Test panel role prompts."""

    def test_all_roles_have_prompts(self):
        """Test that all panel roles have defined prompts."""
        from tessera.panel import (
            CREATIVE_EVALUATOR_PROMPT,
            EFFICIENCY_EVALUATOR_PROMPT,
            RISK_EVALUATOR_PROMPT,
            TECHNICAL_EVALUATOR_PROMPT,
            USER_CENTRIC_EVALUATOR_PROMPT,
        )

        prompts = [
            TECHNICAL_EVALUATOR_PROMPT,
            CREATIVE_EVALUATOR_PROMPT,
            EFFICIENCY_EVALUATOR_PROMPT,
            USER_CENTRIC_EVALUATOR_PROMPT,
            RISK_EVALUATOR_PROMPT,
        ]

        for prompt in prompts:
            assert len(prompt) > 0
            assert "Evaluator" in prompt

    def test_panel_roles_have_different_focuses(self, test_config):
        """Test that different panel roles have different scoring weights."""
        panel = PanelSystem(config=test_config)
        panel.create_default_panel(num_panelists=5)

        # Check that weights differ between panelists
        weights_sets = [tuple(sorted(p.scoring_weights.items())) for p in panel.panelists]

        # At least some should be different
        assert len(set(weights_sets)) > 1


@pytest.mark.unit
class TestPanelVoting:
    """Test panel voting logic."""

    def test_majority_vote_hire(self, mock_llm_with_response, test_config):
        """Test that majority HIRE votes result in hire decision."""
        panel = PanelSystem(config=test_config)
        panel.create_default_panel(num_panelists=5)

        # Create ballot response with HIRE vote
        hire_response = """
        {
            "metrics": {
                "accuracy": 5, "relevance": 5, "completeness": 5,
                "explainability": 5, "efficiency": 5, "safety": 5
            },
            "overall_score": 100.0,
            "rationale": "Excellent",
            "vote": "HIRE"
        }
        """

        # Mock all panelists to vote HIRE
        for panelist in panel.panelists:
            panelist.llm = mock_llm_with_response(hire_response)

        # Mock interviewer
        questions_response = """
        {
            "questions": [{
                "question_id": "Q1",
                "text": "Test",
                "type": "sample",
                "evaluation_focus": "general"
            }]
        }
        """
        panel.interviewer.llm = mock_llm_with_response(questions_response)

        candidate_llms = {
            "Candidate": mock_llm_with_response("Great answer"),
        }

        result = panel.conduct_panel_interview(
            task_description="Test",
            candidates=["Candidate"],
            candidate_llms=candidate_llms,
        )

        # With all HIRE votes, decision should be made
        assert result.decision == "Candidate"
        assert result.confidence in ["high", "medium"]
