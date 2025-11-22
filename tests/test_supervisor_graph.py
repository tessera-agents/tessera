"""Unit tests for SupervisorGraph (LangGraph version)."""

import pytest

from tessera.graph_base import clear_checkpoint_db, get_thread_config
from tessera.supervisor_graph import SupervisorGraph


@pytest.mark.unit
class TestSupervisorGraph:
    """Test SupervisorGraph functionality."""

    def setup_method(self):
        """Clean up checkpoints before each test."""
        clear_checkpoint_db()

    def teardown_method(self):
        """Clean up checkpoints after each test."""
        clear_checkpoint_db()

    def test_supervisor_graph_initialization(self, test_config):
        """Test supervisor graph initialization."""
        supervisor = SupervisorGraph(config=test_config)

        assert supervisor.config == test_config
        assert supervisor.llm is not None
        assert len(supervisor.system_prompt) > 0
        assert supervisor.app is not None

    def test_supervisor_graph_custom_prompt(self, test_config):
        """Test supervisor graph with custom prompt."""
        custom_prompt = "Custom supervisor prompt"
        supervisor = SupervisorGraph(
            config=test_config,
            system_prompt=custom_prompt,
        )

        assert supervisor.system_prompt == custom_prompt

    def test_decompose_task_via_graph(
        self, test_config, sample_task_decomposition, sample_review_response
    ):
        """Test task decomposition through LangGraph."""
        # Create multi-response mock
        from unittest.mock import Mock

        from langchain_core.messages import AIMessage

        responses = [
            sample_task_decomposition,  # decompose
            sample_review_response,  # review subtask 1
            sample_review_response,  # review subtask 2
            "Final synthesized output",  # synthesize
        ]
        call_count = [0]

        def multi_response_invoke(*args, **kwargs):
            response = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
            return AIMessage(content=response)

        llm = Mock()
        llm.invoke = multi_response_invoke

        supervisor = SupervisorGraph(llm=llm, config=test_config)

        config = get_thread_config("test-decompose")
        result = supervisor.invoke(
            {
                "objective": "Build a web scraping system",
            },
            config=config,
        )

        assert result["task_id"] is not None
        assert result["task"] is not None
        assert result["task"]["goal"] == "Build a web scraping system with database storage"
        assert len(result["task"]["subtasks"]) == 2

    def test_graph_state_persistence(
        self, test_config, sample_task_decomposition, sample_review_response
    ):
        """Test that state is persisted to checkpoint."""
        # Create multi-response mock
        from unittest.mock import Mock

        from langchain_core.messages import AIMessage

        responses = [
            sample_task_decomposition,
            sample_review_response,
            sample_review_response,
            "Final output",
        ]
        call_count = [0]

        def multi_response_invoke(*args, **kwargs):
            response = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
            return AIMessage(content=response)

        llm = Mock()
        llm.invoke = multi_response_invoke

        supervisor = SupervisorGraph(llm=llm, config=test_config)

        thread_id = "test-persistence"
        config = get_thread_config(thread_id)

        # First invocation
        result1 = supervisor.invoke(
            {
                "objective": "Build a web scraping system",
            },
            config=config,
        )

        assert result1["task_id"] is not None

        # Get state from checkpoint
        state = supervisor.get_state(config)
        assert state.values["task_id"] == result1["task_id"]

    def test_graph_resume_from_checkpoint(
        self, test_config, sample_task_decomposition, sample_review_response
    ):
        """Test resuming from a checkpoint."""
        # Create multi-response mock
        from unittest.mock import Mock

        from langchain_core.messages import AIMessage

        responses = [
            sample_task_decomposition,
            sample_review_response,
            sample_review_response,
            "Final output",
        ]
        call_count = [0]

        def multi_response_invoke(*args, **kwargs):
            response = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
            return AIMessage(content=response)

        llm = Mock()
        llm.invoke = multi_response_invoke

        supervisor = SupervisorGraph(llm=llm, config=test_config)

        thread_id = "test-resume"
        config = get_thread_config(thread_id)

        # First invocation - stops at first checkpoint
        result1 = supervisor.invoke(
            {
                "objective": "Build a web scraping system",
            },
            config=config,
        )

        task_id = result1["task_id"]

        # Create new instance to simulate restart
        supervisor2 = SupervisorGraph(llm=llm, config=test_config)

        # Resume from checkpoint
        state = supervisor2.get_state(config)
        assert state.values["task_id"] == task_id

    def test_graph_streaming(self, test_config, sample_task_decomposition, sample_review_response):
        """Test streaming graph execution."""
        # Create multi-response mock
        from unittest.mock import Mock

        from langchain_core.messages import AIMessage

        responses = [
            sample_task_decomposition,
            sample_review_response,
            sample_review_response,
            "Final output",
        ]
        call_count = [0]

        def multi_response_invoke(*args, **kwargs):
            response = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
            return AIMessage(content=response)

        llm = Mock()
        llm.invoke = multi_response_invoke

        supervisor = SupervisorGraph(llm=llm, config=test_config)

        config = get_thread_config("test-stream")

        states = list(
            supervisor.stream(
                {
                    "objective": "Build a web scraping system",
                },
                config=config,
            )
        )

        # Should have multiple state updates
        assert len(states) > 0

        # Final state should have task_id
        # Stream returns dicts like {'node_name': {...state...}}
        # Extract all state values
        all_states = []
        for state_update in states:
            for state_data in state_update.values():
                if isinstance(state_data, dict):
                    all_states.append(state_data)

        assert any("task_id" in s for s in all_states)

    def test_graph_handles_multiple_threads(
        self, test_config, sample_task_decomposition, sample_review_response
    ):
        """Test handling multiple independent threads."""
        # Create multi-response mock
        from unittest.mock import Mock

        from langchain_core.messages import AIMessage

        responses = [
            sample_task_decomposition,
            sample_review_response,
            sample_review_response,
            "Final output",
        ]
        call_count = [0]

        def multi_response_invoke(*args, **kwargs):
            response = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
            return AIMessage(content=response)

        llm = Mock()
        llm.invoke = multi_response_invoke

        supervisor = SupervisorGraph(llm=llm, config=test_config)

        # Thread 1
        config1 = get_thread_config("thread-1")
        result1 = supervisor.invoke(
            {"objective": "Task 1"},
            config=config1,
        )

        # Reset call count for thread 2
        call_count[0] = 0

        # Thread 2
        config2 = get_thread_config("thread-2")
        result2 = supervisor.invoke(
            {"objective": "Task 2"},
            config=config2,
        )

        # Should have different task IDs
        assert result1["task_id"] != result2["task_id"]

        # States should be independent
        state1 = supervisor.get_state(config1)
        state2 = supervisor.get_state(config2)
        assert state1.values["task_id"] != state2.values["task_id"]

    def test_graph_decompose_node_creates_task(
        self, mock_llm_with_response, test_config, sample_task_decomposition
    ):
        """Test decompose node creates proper task structure."""
        llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorGraph(llm=llm, config=test_config)

        # Call decompose node directly
        state = {
            "objective": "Build a web scraping system",
            "thread_id": None,
            "task_id": None,
            "task": None,
            "current_subtask_id": None,
            "current_subtask": None,
            "agent_name": None,
            "agent_response": None,
            "review_result": None,
            "completed_subtasks": [],
            "final_output": None,
            "next_action": None,
        }

        result = supervisor._decompose_node(state)

        assert result["task_id"] is not None
        assert result["task"] is not None
        assert result["task"]["goal"] == "Build a web scraping system with database storage"
        assert len(result["task"]["subtasks"]) == 2
        assert result["next_action"] == "assign"

    def test_graph_assign_node_finds_available_subtask(
        self, mock_llm_with_response, test_config, sample_task_decomposition
    ):
        """Test assign node finds and assigns available subtask."""
        llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorGraph(llm=llm, config=test_config)

        # First decompose
        state = {
            "objective": "Build a web scraping system",
            "thread_id": None,
            "task_id": None,
            "task": None,
            "current_subtask_id": None,
            "current_subtask": None,
            "agent_name": None,
            "agent_response": None,
            "review_result": None,
            "completed_subtasks": [],
            "final_output": None,
            "next_action": None,
        }

        decompose_result = supervisor._decompose_node(state)

        # Then assign
        assign_result = supervisor._assign_node(decompose_result)

        assert assign_result["current_subtask_id"] is not None
        assert assign_result["current_subtask"] is not None
        assert assign_result["agent_name"] == "default_agent"
        assert assign_result["next_action"] == "execute"

    def test_graph_execute_node_simulates_execution(
        self, mock_llm_with_response, test_config, sample_task_decomposition
    ):
        """Test execute node simulates subtask execution."""
        llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorGraph(llm=llm, config=test_config)

        state = {
            "objective": "Build a web scraping system",
            "thread_id": None,
            "task_id": "test_task",
            "task": {"goal": "test"},
            "current_subtask_id": "subtask_1",
            "current_subtask": {
                "task_id": "subtask_1",
                "description": "Test subtask",
            },
            "agent_name": "test_agent",
            "agent_response": None,
            "review_result": None,
            "completed_subtasks": [],
            "final_output": None,
            "next_action": None,
        }

        result = supervisor._execute_node(state)

        assert result["agent_response"] is not None
        assert "content" in result["agent_response"]
        assert result["next_action"] == "review"

    def test_graph_routing_after_decompose(
        self, mock_llm_with_response, test_config, sample_task_decomposition
    ):
        """Test routing logic after decomposition."""
        llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorGraph(llm=llm, config=test_config)

        # State with task -> should route to assign
        state_with_task = {"task": {"subtasks": [{"task_id": "st1"}]}}
        assert supervisor._route_after_decompose(state_with_task) == "assign"

        # State without task -> should route to end
        state_without_task = {"task": None}
        assert supervisor._route_after_decompose(state_without_task) == "end"

    def test_graph_full_execution_flow(
        self, test_config, sample_task_decomposition, sample_review_response
    ):
        """Test full execution flow through the graph."""
        # Need to mock multiple responses for different stages
        from unittest.mock import Mock

        from langchain_core.messages import AIMessage

        responses = [
            sample_task_decomposition,  # decompose
            sample_review_response,  # review subtask 1
            sample_review_response,  # review subtask 2
            "Final synthesized output",  # synthesize
        ]

        call_count = [0]

        def multi_response_invoke(*args, **kwargs):
            response = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
            return AIMessage(content=response)

        llm = Mock()
        llm.invoke = multi_response_invoke

        supervisor = SupervisorGraph(llm=llm, config=test_config)

        config = get_thread_config("test-full-flow")
        result = supervisor.invoke(
            {"objective": "Build a web scraping system"},
            config=config,
        )

        # Should have completed execution
        assert result["task_id"] is not None
        assert result["task"] is not None


@pytest.fixture
def sample_review_response():
    """Sample review response JSON."""
    return """{
        "approved": true,
        "quality": "high",
        "feedback": "Excellent work",
        "missing_criteria": [],
        "redirect_needed": false,
        "redirect_prompt": ""
    }"""
