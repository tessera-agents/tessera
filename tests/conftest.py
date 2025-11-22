"""Pytest configuration and shared fixtures."""

from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import AIMessage

from tessera.config import FrameworkConfig, LLMConfig, ScoringWeights


# Auto-use fixture to mock LLM creation globally
@pytest.fixture(autouse=True)
def mock_llm_creation():
    """Automatically mock LLM creation for all tests."""

    def mock_create_llm(*args, **kwargs):
        llm = Mock()
        llm.invoke = Mock(return_value=AIMessage(content='{"result": "test"}'))
        return llm

    with patch("tessera.llm.create_llm", side_effect=mock_create_llm):
        with patch("tessera.llm.ChatLiteLLM", return_value=mock_create_llm()):
            yield


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    llm = Mock()
    llm.invoke = Mock(return_value=AIMessage(content='{"result": "test"}'))
    return llm


@pytest.fixture
def mock_llm_with_response():
    """Create a mock LLM that returns custom responses."""

    def _create_mock(response_content: str):
        llm = Mock()
        llm.invoke = Mock(return_value=AIMessage(content=response_content))
        return llm

    return _create_mock


@pytest.fixture
def test_config():
    """Create a test configuration."""
    llm_config = LLMConfig(
        provider="openai",
        api_key="test-key-for-testing",
        models=["gpt-4-turbo-preview"],
        temperature=0.7,
    )
    return FrameworkConfig(
        llm=llm_config,
        scoring_weights=ScoringWeights(),
        max_iterations=10,
        enable_logging=False,
    )


@pytest.fixture
def scoring_weights():
    """Create default scoring weights."""
    return ScoringWeights(
        accuracy=0.30,
        relevance=0.20,
        completeness=0.15,
        explainability=0.10,
        efficiency=0.10,
        safety=0.15,
    )


@pytest.fixture
def sample_task_description():
    """Sample task description for testing."""
    return "Design a caching strategy for a high-traffic API service"


@pytest.fixture
def sample_questions():
    """Sample interview questions for testing."""
    return [
        {
            "question_id": "Q1",
            "text": "How would you implement cache invalidation?",
            "type": "sample",
            "evaluation_focus": "technical accuracy",
        },
        {
            "question_id": "Q2",
            "text": "What edge cases would you consider?",
            "type": "edge-case",
            "evaluation_focus": "completeness",
        },
        {
            "question_id": "Q3",
            "text": "What are the limitations of your approach?",
            "type": "meta",
            "evaluation_focus": "self-awareness",
        },
    ]


@pytest.fixture
def sample_score_response():
    """Sample score response JSON."""
    return """{
        "metrics": {
            "accuracy": 4,
            "relevance": 5,
            "completeness": 3,
            "explainability": 4,
            "efficiency": 3,
            "safety": 5
        },
        "rationale": "Good technical approach with clear explanation.",
        "overall_score": 82.0
    }"""


@pytest.fixture
def sample_ballot_response():
    """Sample ballot response JSON."""
    return """{
        "metrics": {
            "accuracy": 4,
            "relevance": 4,
            "completeness": 4,
            "explainability": 3,
            "efficiency": 3,
            "safety": 4
        },
        "overall_score": 78.0,
        "rationale": "Solid approach with room for improvement.",
        "vote": "HIRE"
    }"""


@pytest.fixture
def sample_task_decomposition():
    """Sample task decomposition response."""
    return """{
        "goal": "Build a web scraping system with database storage",
        "subtasks": [
            {
                "task_id": "subtask_1",
                "description": "Design scraper architecture",
                "acceptance_criteria": ["Modular design", "Error handling"],
                "dependencies": []
            },
            {
                "task_id": "subtask_2",
                "description": "Implement database schema",
                "acceptance_criteria": ["Normalized schema", "Indexes defined"],
                "dependencies": ["subtask_1"]
            }
        ]
    }"""


@pytest.fixture
def sample_review_response():
    """Sample review response JSON."""
    return """{
        "approved": true,
        "quality": "high",
        "feedback": "Excellent implementation meeting all criteria.",
        "missing_criteria": [],
        "redirect_needed": false,
        "redirect_prompt": ""
    }"""


@pytest.fixture
def sample_recommendation_response():
    """Sample recommendation response JSON."""
    return """{
        "recommendation": "approve - strong technical capability",
        "weaknesses": ["Could improve error handling details"],
        "guardrails": ["Monitor cache hit rates", "Set up alerts for cache failures"]
    }"""


@pytest.fixture
def sample_comparison_response():
    """Sample comparison response JSON."""
    return """{
        "selected_candidate": "CandidateA",
        "justification": "CandidateA demonstrated superior technical depth and practical experience.",
        "key_differentiators": ["Better error handling", "More scalable approach"],
        "confidence": "High",
        "runner_up": "CandidateB"
    }"""
