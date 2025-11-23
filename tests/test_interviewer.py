"""Unit tests for Interviewer agent."""

import json

import pytest

from tessera.config import ScoringWeights
from tessera.interviewer import InterviewerAgent
from tessera.models import InterviewResult, QuestionResponse, ScoreMetrics


@pytest.mark.unit
class TestInterviewerAgent:
    """Test Interviewer agent functionality."""

    def test_interviewer_initialization(self, test_config):
        """Test interviewer initialization."""
        interviewer = InterviewerAgent(config=test_config)

        assert interviewer.config == test_config
        assert interviewer.llm is not None
        assert len(interviewer.system_prompt) > 0
        assert isinstance(interviewer.scoring_weights, ScoringWeights)

    def test_interviewer_custom_prompt(self, test_config):
        """Test interviewer with custom prompt."""
        custom_prompt = "Custom interviewer prompt"
        interviewer = InterviewerAgent(
            config=test_config,
            system_prompt=custom_prompt,
        )

        assert interviewer.system_prompt == custom_prompt

    def test_design_interview(self, mock_llm_with_response, test_config):
        """Test designing interview questions."""
        questions_response = json.dumps(
            {
                "questions": [
                    {
                        "question_id": "Q1",
                        "text": "How would you implement caching?",
                        "type": "sample",
                        "evaluation_focus": "technical accuracy",
                    },
                    {
                        "question_id": "Q2",
                        "text": "What edge cases exist?",
                        "type": "edge-case",
                        "evaluation_focus": "completeness",
                    },
                ]
            }
        )

        llm = mock_llm_with_response(questions_response)
        interviewer = InterviewerAgent(llm=llm, config=test_config)

        questions = interviewer.design_interview("Design a caching strategy", num_questions=2)

        assert len(questions) == 2
        assert questions[0]["question_id"] == "Q1"
        assert questions[1]["type"] == "edge-case"

    def test_conduct_interview(
        self,
        mock_llm_with_response,
        test_config,
        sample_questions,
        sample_score_response,
        sample_recommendation_response,
    ):
        """Test conducting an interview."""
        # Mock for scoring
        score_llm = mock_llm_with_response(sample_score_response)
        interviewer = InterviewerAgent(llm=score_llm, config=test_config)

        # Mock candidate LLM
        candidate_llm = mock_llm_with_response("I would implement a Redis-based cache...")

        # Create recommendation mock
        rec_llm = mock_llm_with_response(sample_recommendation_response)

        # Patch the recommendation generation
        original_generate = interviewer._generate_recommendation

        def mock_generate(*args, **kwargs):
            interviewer.llm = rec_llm
            result = original_generate(*args, **kwargs)
            interviewer.llm = score_llm  # Restore
            return result

        interviewer._generate_recommendation = mock_generate

        result = interviewer.conduct_interview(
            candidate_name="TestCandidate",
            candidate_llm=candidate_llm,
            questions=sample_questions,
            task_description="Design a caching strategy",
        )

        assert result.candidate == "TestCandidate"
        assert len(result.questions) == len(sample_questions)
        assert len(result.scores) == len(sample_questions)
        assert result.aggregated_score > 0
        assert result.recommendation is not None

    def test_calculate_weighted_score(self, test_config):
        """Test weighted score calculation."""
        interviewer = InterviewerAgent(config=test_config)

        metrics = ScoreMetrics(
            accuracy=4.0,
            relevance=5.0,
            completeness=3.0,
            explainability=4.0,
            efficiency=3.0,
            safety=5.0,
        )

        score = interviewer._calculate_weighted_score(metrics)

        # Should be weighted average normalized to 0-100
        assert 0 <= score <= 100
        assert isinstance(score, float)

    def test_calculate_weighted_score_perfect(self, test_config):
        """Test weighted score with perfect metrics."""
        interviewer = InterviewerAgent(config=test_config)

        metrics = ScoreMetrics(
            accuracy=5.0,
            relevance=5.0,
            completeness=5.0,
            explainability=5.0,
            efficiency=5.0,
            safety=5.0,
        )

        score = interviewer._calculate_weighted_score(metrics)

        assert score == 100.0

    def test_calculate_weighted_score_zero(self, test_config):
        """Test weighted score with zero metrics."""
        interviewer = InterviewerAgent(config=test_config)

        metrics = ScoreMetrics(
            accuracy=0.0,
            relevance=0.0,
            completeness=0.0,
            explainability=0.0,
            efficiency=0.0,
            safety=0.0,
        )

        score = interviewer._calculate_weighted_score(metrics)

        assert score == 0.0

    def test_compare_candidates(self, mock_llm_with_response, test_config, sample_comparison_response):
        """Test comparing multiple candidates."""
        llm = mock_llm_with_response(sample_comparison_response)
        interviewer = InterviewerAgent(llm=llm, config=test_config)

        # Create mock interview results
        result1 = InterviewResult(
            candidate="CandidateA",
            aggregated_score=85.0,
            recommendation="approve",
        )
        result2 = InterviewResult(
            candidate="CandidateB",
            aggregated_score=78.0,
            recommendation="conditional",
        )
        result3 = InterviewResult(
            candidate="CandidateC",
            aggregated_score=92.0,
            recommendation="approve",
        )

        comparison = interviewer.compare_candidates([result1, result2, result3])

        assert "rankings" in comparison
        assert len(comparison["rankings"]) == 3
        assert comparison["rankings"][0]["candidate"] == "CandidateC"  # Highest score
        assert comparison["rankings"][0]["rank"] == 1
        assert comparison["selected_candidate"] == "CandidateA"  # From LLM response
        assert "confidence" in comparison

    def test_compare_candidates_empty(self, test_config):
        """Test comparing with no candidates."""
        interviewer = InterviewerAgent(config=test_config)

        comparison = interviewer.compare_candidates([])

        assert "error" in comparison

    def test_compare_candidates_assigns_rankings(self, mock_llm_with_response, test_config, sample_comparison_response):
        """Test that compare_candidates assigns rankings to results."""
        llm = mock_llm_with_response(sample_comparison_response)
        interviewer = InterviewerAgent(llm=llm, config=test_config)

        result1 = InterviewResult(candidate="A", aggregated_score=70.0)
        result2 = InterviewResult(candidate="B", aggregated_score=90.0)

        interviewer.compare_candidates([result1, result2])

        assert result2.ranking == 1  # Higher score
        assert result1.ranking == 2

    def test_break_tie(self, mock_llm_with_response, test_config):
        """Test breaking a tie between candidates."""
        # Mock for tie-breaker question
        question_response = json.dumps(
            {
                "question": "Design a failover strategy for your cache",
                "evaluation_focus": "resilience and planning",
            }
        )

        # Mock for evaluation
        eval_response = json.dumps(
            {
                "selected_candidate": "CandidateA",
                "justification": "Better handling of edge cases",
                "scores": {"CandidateA": 88, "CandidateB": 82},
            }
        )

        # Create interviewer with question mock
        question_llm = mock_llm_with_response(question_response)
        interviewer = InterviewerAgent(llm=question_llm, config=test_config)

        # Create candidate LLMs
        candidate_llms = {
            "CandidateA": mock_llm_with_response("I would implement active-passive failover..."),
            "CandidateB": mock_llm_with_response("I would use lazy replication..."),
        }

        # Switch to eval mock after question
        eval_llm = mock_llm_with_response(eval_response)

        # Capture original invoke
        original_invoke = interviewer.llm.invoke
        invoke_count = [0]

        def counted_invoke(*args, **kwargs):
            invoke_count[0] += 1
            if invoke_count[0] == 1:
                return original_invoke(*args, **kwargs)
            return eval_llm.invoke(*args, **kwargs)

        interviewer.llm.invoke = counted_invoke

        decision = interviewer.break_tie(
            tied_candidates=["CandidateA", "CandidateB"],
            candidate_llms=candidate_llms,
            task_description="Design caching strategy",
        )

        assert decision["selected_candidate"] == "CandidateA"
        assert "justification" in decision
        assert "tiebreaker_question" in decision
        assert len(decision["responses"]) == 2

    def test_parse_json_response(self, test_config):
        """Test JSON parsing from various formats."""
        interviewer = InterviewerAgent(config=test_config)

        # Plain JSON
        result = interviewer._parse_json_response('{"key": "value"}')
        assert result["key"] == "value"

        # JSON in markdown code block
        result = interviewer._parse_json_response('```json\n{"key": "value"}\n```')
        assert result["key"] == "value"

    def test_format_results_for_comparison(self, test_config):
        """Test formatting results for comparison."""
        interviewer = InterviewerAgent(config=test_config)

        results = [
            InterviewResult(
                candidate="CandidateA",
                aggregated_score=85.0,
                recommendation="approve",
                weaknesses=["timing", "edge cases"],
            ),
            InterviewResult(
                candidate="CandidateB",
                aggregated_score=78.0,
                recommendation="conditional",
                weaknesses=[],
            ),
        ]

        formatted = interviewer._format_results_for_comparison(results)

        assert "CandidateA" in formatted
        assert "CandidateB" in formatted
        assert "85.0" in formatted
        assert "78.0" in formatted

    def test_score_responses(self, mock_llm_with_response, test_config, sample_questions, sample_score_response):
        """Test scoring responses."""
        llm = mock_llm_with_response(sample_score_response)
        interviewer = InterviewerAgent(llm=llm, config=test_config)

        responses = [
            QuestionResponse(
                question_id="Q1",
                question_text="Question 1",
                answer="Answer 1",
            ),
            QuestionResponse(
                question_id="Q2",
                question_text="Question 2",
                answer="Answer 2",
            ),
        ]

        scores = interviewer._score_responses(
            candidate_name="TestCandidate",
            questions=sample_questions[:2],
            responses=responses,
            task_description="Test task",
        )

        assert len(scores) == 2
        assert all(s.candidate == "TestCandidate" for s in scores)
        assert all(s.overall_score > 0 for s in scores)

    def test_generate_recommendation(self, mock_llm_with_response, test_config, sample_recommendation_response):
        """Test generating recommendation."""
        llm = mock_llm_with_response(sample_recommendation_response)
        interviewer = InterviewerAgent(llm=llm, config=test_config)

        responses = [
            QuestionResponse(question_id="Q1", question_text="Q1", answer="A1"),
        ]

        from tessera.models import Score

        scores = [
            Score(
                question_id="Q1",
                candidate="TestCandidate",
                panelist="interviewer",
                metrics=ScoreMetrics(
                    accuracy=4.0,
                    relevance=4.0,
                    completeness=4.0,
                    explainability=3.0,
                    efficiency=3.0,
                    safety=4.0,
                ),
                rationale="Good answer",
                overall_score=80.0,
            )
        ]

        recommendation = interviewer._generate_recommendation(
            candidate_name="TestCandidate",
            aggregated_score=80.0,
            responses=responses,
            scores=scores,
        )

        assert "recommendation" in recommendation
        assert "weaknesses" in recommendation
        assert "guardrails" in recommendation
