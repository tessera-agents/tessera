"""Unit tests for Supervisor agent."""

import pytest

from tessera.models import AgentResponse, TaskStatus
from tessera.supervisor import SupervisorAgent


@pytest.mark.unit
class TestSupervisorAgent:
    """Test Supervisor agent functionality."""

    def test_supervisor_initialization(self, test_config):
        """Test supervisor initialization."""
        supervisor = SupervisorAgent(config=test_config)

        assert supervisor.config == test_config
        assert supervisor.llm is not None
        assert len(supervisor.system_prompt) > 0
        assert len(supervisor.tasks) == 0

    def test_supervisor_custom_prompt(self, test_config):
        """Test supervisor with custom prompt."""
        custom_prompt = "Custom supervisor prompt"
        supervisor = SupervisorAgent(
            config=test_config,
            system_prompt=custom_prompt,
        )

        assert supervisor.system_prompt == custom_prompt

    def test_decompose_task(self, mock_llm_with_response, test_config, sample_task_decomposition):
        """Test task decomposition."""
        llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorAgent(llm=llm, config=test_config)

        task = supervisor.decompose_task("Build a web scraping system")

        assert task.goal == "Build a web scraping system with database storage"
        assert len(task.subtasks) == 2
        assert task.subtasks[0].task_id == "subtask_1"
        assert task.subtasks[1].task_id == "subtask_2"
        assert len(task.subtasks[0].acceptance_criteria) == 2
        assert task.subtasks[1].dependencies == ["subtask_1"]

    def test_decompose_task_stores_in_tasks_dict(
        self, mock_llm_with_response, test_config, sample_task_decomposition
    ):
        """Test task decomposition stores task in tasks dictionary."""
        llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorAgent(llm=llm, config=test_config)

        task = supervisor.decompose_task("Build a web scraping system")

        assert task.task_id in supervisor.tasks
        assert supervisor.tasks[task.task_id] == task

    def test_assign_subtask(self, mock_llm_with_response, test_config, sample_task_decomposition):
        """Test assigning a subtask to an agent."""
        llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorAgent(llm=llm, config=test_config)

        task = supervisor.decompose_task("Build a web scraping system")
        subtask_id = task.subtasks[0].task_id

        supervisor.assign_subtask(task.task_id, subtask_id, "agent_scraper")

        assigned_subtask = supervisor.tasks[task.task_id].subtasks[0]
        assert assigned_subtask.assigned_to == "agent_scraper"
        assert assigned_subtask.status == TaskStatus.PENDING

    def test_assign_subtask_invalid_task(self, test_config):
        """Test assigning subtask with invalid task ID raises error."""
        supervisor = SupervisorAgent(config=test_config)

        with pytest.raises(ValueError, match="Task .* not found"):
            supervisor.assign_subtask("invalid_task_id", "subtask_1", "agent_1")

    def test_update_subtask_status(
        self, mock_llm_with_response, test_config, sample_task_decomposition
    ):
        """Test updating subtask status."""
        llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorAgent(llm=llm, config=test_config)

        task = supervisor.decompose_task("Build a web scraping system")
        subtask_id = task.subtasks[0].task_id

        supervisor.update_subtask_status(
            task.task_id,
            subtask_id,
            TaskStatus.COMPLETED,
            "Task completed successfully",
        )

        updated_subtask = supervisor.tasks[task.task_id].subtasks[0]
        assert updated_subtask.status == TaskStatus.COMPLETED
        assert updated_subtask.result == "Task completed successfully"

    def test_update_subtask_status_invalid_task(self, test_config):
        """Test updating status with invalid task ID raises error."""
        supervisor = SupervisorAgent(config=test_config)

        with pytest.raises(ValueError, match="Task .* not found"):
            supervisor.update_subtask_status(
                "invalid_task_id",
                "subtask_1",
                TaskStatus.COMPLETED,
            )

    def test_review_agent_output(
        self, mock_llm_with_response, test_config, sample_task_decomposition, sample_review_response
    ):
        """Test reviewing agent output."""
        # First decompose a task
        decomp_llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorAgent(llm=decomp_llm, config=test_config)
        task = supervisor.decompose_task("Build a web scraping system")

        # Then review with a different mock
        review_llm = mock_llm_with_response(sample_review_response)
        supervisor.llm = review_llm

        subtask_id = task.subtasks[0].task_id
        response = AgentResponse(
            agent_name="agent_scraper",
            task_id=subtask_id,
            content="Implemented Scrapy-based scraper",
        )

        review = supervisor.review_agent_output(task.task_id, subtask_id, response)

        assert review["approved"] is True
        assert review["quality"] == "high"
        assert len(review["feedback"]) > 0
        assert review["redirect_needed"] is False

    def test_review_agent_output_invalid_task(self, test_config):
        """Test reviewing output with invalid task ID raises error."""
        supervisor = SupervisorAgent(config=test_config)
        response = AgentResponse(
            agent_name="agent_1",
            task_id="subtask_1",
            content="test",
        )

        with pytest.raises(ValueError, match="Task .* not found"):
            supervisor.review_agent_output("invalid_task_id", "subtask_1", response)

    def test_get_task_status(self, mock_llm_with_response, test_config, sample_task_decomposition):
        """Test getting task status."""
        llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorAgent(llm=llm, config=test_config)

        task = supervisor.decompose_task("Build a web scraping system")
        status = supervisor.get_task_status(task.task_id)

        assert status["task_id"] == task.task_id
        assert status["goal"] == task.goal
        assert "created_at" in status
        assert "last_updated" in status
        assert len(status["subtasks"]) == 2

    def test_get_task_status_invalid_task(self, test_config):
        """Test getting status with invalid task ID raises error."""
        supervisor = SupervisorAgent(config=test_config)

        with pytest.raises(ValueError, match="Task .* not found"):
            supervisor.get_task_status("invalid_task_id")

    def test_request_interviewer_evaluation(self, test_config):
        """Test requesting interviewer evaluation."""
        supervisor = SupervisorAgent(config=test_config)

        request = supervisor.request_interviewer_evaluation(
            task_description="Complex database task",
            candidates=["agent_1", "agent_2", "agent_3"],
        )

        assert request["action"] == "interview_request"
        assert request["task_description"] == "Complex database task"
        assert len(request["candidates"]) == 3
        assert "timestamp" in request

    def test_parse_json_response(self, test_config):
        """Test JSON parsing from various formats."""
        supervisor = SupervisorAgent(config=test_config)

        # Plain JSON
        result = supervisor._parse_json_response('{"key": "value"}')
        assert result["key"] == "value"

        # JSON in markdown code block
        result = supervisor._parse_json_response('```json\n{"key": "value"}\n```')
        assert result["key"] == "value"

        # JSON in code block without language
        result = supervisor._parse_json_response('```\n{"key": "value"}\n```')
        assert result["key"] == "value"

    def test_parse_json_response_invalid(self, test_config):
        """Test JSON parsing with invalid JSON raises error."""
        supervisor = SupervisorAgent(config=test_config)

        with pytest.raises(ValueError, match="Failed to parse JSON"):
            supervisor._parse_json_response("not valid json at all")

    def test_synthesize_results(
        self, mock_llm_with_response, test_config, sample_task_decomposition
    ):
        """Test synthesizing results from completed subtasks."""
        # Decompose task
        decomp_llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorAgent(llm=decomp_llm, config=test_config)
        task = supervisor.decompose_task("Build a web scraping system")

        # Mark subtasks as completed
        supervisor.update_subtask_status(
            task.task_id,
            task.subtasks[0].task_id,
            TaskStatus.COMPLETED,
            "Scraper architecture designed",
        )
        supervisor.update_subtask_status(
            task.task_id,
            task.subtasks[1].task_id,
            TaskStatus.COMPLETED,
            "Database schema implemented",
        )

        # Synthesize
        synthesis_llm = mock_llm_with_response("Final synthesis of all completed work")
        supervisor.llm = synthesis_llm

        result = supervisor.synthesize_results(task.task_id)

        assert len(result) > 0
        assert "synthesis" in result.lower() or "Final" in result

    def test_synthesize_results_no_completed_subtasks(
        self, mock_llm_with_response, test_config, sample_task_decomposition
    ):
        """Test synthesizing when no subtasks are completed."""
        llm = mock_llm_with_response(sample_task_decomposition)
        supervisor = SupervisorAgent(llm=llm, config=test_config)
        task = supervisor.decompose_task("Build a web scraping system")

        result = supervisor.synthesize_results(task.task_id)

        assert "No completed subtasks" in result

    def test_synthesize_results_invalid_task(self, test_config):
        """Test synthesizing with invalid task ID raises error."""
        supervisor = SupervisorAgent(config=test_config)

        with pytest.raises(ValueError, match="Task .* not found"):
            supervisor.synthesize_results("invalid_task_id")
