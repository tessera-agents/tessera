"""Unit tests for InterviewerGraph (LangGraph version)."""

import pytest

from tessera.graph_base import clear_checkpoint_db, get_thread_config
from tessera.interviewer_graph import InterviewerGraph


@pytest.mark.unit
class TestInterviewerGraph:
    """Test InterviewerGraph functionality."""

    def setup_method(self):
        """Clean up checkpoints before each test."""
        clear_checkpoint_db()

    def teardown_method(self):
        """Clean up checkpoints after each test."""
        clear_checkpoint_db()

    def test_interviewer_graph_initialization(self, test_config):
        """Test interviewer graph initialization."""
        interviewer = InterviewerGraph(config=test_config)

        assert interviewer.config == test_config
        assert interviewer.llm is not None
        assert len(interviewer.system_prompt) > 0
        assert interviewer.app is not None

    def test_interviewer_graph_custom_prompt(self, test_config):
        """Test interviewer graph with custom prompt."""
        custom_prompt = "Custom interviewer prompt"
        interviewer = InterviewerGraph(
            config=test_config,
            system_prompt=custom_prompt,
        )

        assert interviewer.system_prompt == custom_prompt

    def test_design_questions_via_graph(self, test_config):
        """Test question design through LangGraph."""
        from unittest.mock import Mock

        from langchain_core.messages import AIMessage

        # Mock responses for all stages
        responses = [
            """{"questions": [
                {"question_id": "Q1", "text": "How would you implement caching?", "type": "sample", "evaluation_focus": "technical"},
                {"question_id": "Q2", "text": "Handle cache invalidation?", "type": "edge-case", "evaluation_focus": "robustness"}
            ]}""",  # design
            """{"accuracy": 4, "relevance": 5, "completeness": 3, "explainability": 4, "efficiency": 3, "safety": 5}""",  # score Q1
            """{"accuracy": 3, "relevance": 4, "completeness": 4, "explainability": 3, "efficiency": 4, "safety": 4}""",  # score Q2
        ]
        call_count = [0]

        def multi_response_invoke(*args, **kwargs):
            response = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
            return AIMessage(content=response)

        llm = Mock()
        llm.invoke = multi_response_invoke

        interviewer = InterviewerGraph(llm=llm, config=test_config)

        config = get_thread_config("test-interview")
        result = interviewer.invoke(
            {
                "task_description": "Build a caching system",
                "candidate_name": "test-candidate",
            },
            config=config,
        )

        assert result["questions"] is not None
        assert len(result["questions"]) == 2
        assert result["overall_score"] is not None
        assert result["recommendation"] is not None

    def test_graph_state_persistence(self, test_config):
        """Test that state is persisted to checkpoint."""
        from unittest.mock import Mock

        from langchain_core.messages import AIMessage

        responses = [
            """{"questions": [{"question_id": "Q1", "text": "Test?", "type": "sample", "evaluation_focus": "test"}]}""",
            """{"accuracy": 4, "relevance": 4, "completeness": 4, "explainability": 4, "efficiency": 4, "safety": 4}""",
        ]
        call_count = [0]

        def multi_response_invoke(*args, **kwargs):
            response = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
            return AIMessage(content=response)

        llm = Mock()
        llm.invoke = multi_response_invoke

        interviewer = InterviewerGraph(llm=llm, config=test_config)

        thread_id = "test-persist"
        config = get_thread_config(thread_id)

        # Run interview
        result = interviewer.invoke(
            {
                "task_description": "Build system",
                "candidate_name": "test",
            },
            config=config,
        )

        assert result["questions"] is not None

        # Get state from checkpoint
        state = interviewer.get_state(config)
        assert state.values["questions"] is not None

    def test_interviewer_graph_streaming(self, test_config):
        """Test streaming graph execution."""
        from unittest.mock import Mock

        from langchain_core.messages import AIMessage

        responses = [
            """{"questions": [{"question_id": "Q1", "text": "Test?", "type": "sample", "evaluation_focus": "test"}]}""",
            """{"accuracy": 4, "relevance": 4, "completeness": 4, "explainability": 4, "efficiency": 4, "safety": 4}""",
        ]
        call_count = [0]

        def multi_response_invoke(*args, **kwargs):
            response = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
            return AIMessage(content=response)

        llm = Mock()
        llm.invoke = multi_response_invoke

        interviewer = InterviewerGraph(llm=llm, config=test_config)

        config = get_thread_config("test-stream")

        states = list(
            interviewer.stream(
                {
                    "task_description": "Build system",
                    "candidate_name": "test",
                },
                config=config,
            )
        )

        # Should have multiple state updates
        assert len(states) > 0

        # Extract all states
        all_states = []
        for state_update in states:
            for state_data in state_update.values():
                if isinstance(state_data, dict):
                    all_states.append(state_data)

        assert any("questions" in s for s in all_states)

    def test_design_node_creates_questions(self, test_config):
        """Test design node creates proper question structure."""
        from unittest.mock import Mock

        from langchain_core.messages import AIMessage

        response_content = """{"questions": [
            {"question_id": "Q1", "text": "Test question", "type": "sample", "evaluation_focus": "testing"}
        ]}"""

        llm = Mock()
        llm.invoke = Mock(return_value=AIMessage(content=response_content))

        interviewer = InterviewerGraph(llm=llm, config=test_config)

        # Call design node directly
        state = {
            "task_description": "Build a system",
            "candidate_name": None,
            "thread_id": None,
            "questions": None,
            "responses": None,
            "scores": None,
            "overall_score": None,
            "recommendation": None,
            "next_action": None,
        }

        result = interviewer._design_node(state)

        assert result["questions"] is not None
        assert len(result["questions"]) == 1
        assert result["questions"][0]["question_id"] == "Q1"
        assert result["next_action"] == "ask_questions"

    def test_interview_node_generates_responses(self, test_config):
        """Test interview node simulates responses."""
        interviewer = InterviewerGraph(config=test_config)

        state = {
            "task_description": "Build a system",
            "candidate_name": "test-candidate",
            "thread_id": None,
            "questions": [
                {"question_id": "Q1", "text": "How would you do X?"},
                {"question_id": "Q2", "text": "What about Y?"},
            ],
            "responses": None,
            "scores": None,
            "overall_score": None,
            "recommendation": None,
            "next_action": None,
        }

        result = interviewer._interview_node(state)

        assert result["responses"] is not None
        assert len(result["responses"]) == 2
        assert result["next_action"] == "score"

    def test_score_node_calculates_scores(self, test_config):
        """Test score node calculates weighted scores."""
        from unittest.mock import Mock

        from langchain_core.messages import AIMessage

        # Mock scoring responses
        score_response = """{"accuracy": 4, "relevance": 5, "completeness": 3, "explainability": 4, "efficiency": 3, "safety": 5}"""

        llm = Mock()
        llm.invoke = Mock(return_value=AIMessage(content=score_response))

        interviewer = InterviewerGraph(llm=llm, config=test_config)

        state = {
            "task_description": "Build a system",
            "candidate_name": "test-candidate",
            "thread_id": None,
            "questions": [
                {"question_id": "Q1", "text": "Test question?"},
            ],
            "responses": [
                {"question_id": "Q1", "question_text": "Test question?", "answer": "Test answer"},
            ],
            "scores": None,
            "overall_score": None,
            "recommendation": None,
            "next_action": None,
        }

        result = interviewer._score_node(state)

        assert result["scores"] is not None
        assert len(result["scores"]) == 1
        assert result["overall_score"] is not None
        assert result["overall_score"] > 0
        assert result["next_action"] == "recommend"

    def test_recommend_node_generates_recommendation(self, test_config):
        """Test recommend node generates proper recommendation."""
        interviewer = InterviewerGraph(config=test_config)

        state = {
            "task_description": "Build a system",
            "candidate_name": "test-candidate",
            "thread_id": None,
            "questions": [],
            "responses": [],
            "scores": [],
            "overall_score": 85.0,
            "recommendation": None,
            "next_action": None,
        }

        result = interviewer._recommend_node(state)

        assert result["recommendation"] is not None
        assert result["recommendation"]["decision"] == "STRONG HIRE"
        assert result["recommendation"]["overall_score"] == 85.0
        assert result["next_action"] == "end"
