"""Tests for async multi-agent executor."""

from unittest.mock import Mock

import pytest

from tessera.models import SubTask, Task
from tessera.observability import MetricsStore
from tessera.workflow import AgentPool, MultiAgentExecutor


@pytest.mark.unit
class TestAsyncMultiAgentExecutor:
    """Test async multi-agent execution."""

    def test_executor_initialization(self):
        """Test executor initialization."""
        mock_supervisor = Mock()
        agent_pool = AgentPool([])
        metrics_store = MetricsStore()

        executor = MultiAgentExecutor(
            supervisor=mock_supervisor,
            agent_pool=agent_pool,
            max_parallel=5,
            max_iterations=20,
            metrics_store=metrics_store,
        )

        assert executor.supervisor == mock_supervisor
        assert executor.agent_pool == agent_pool
        assert executor.max_parallel == 5
        assert executor.max_iterations == 20
        assert executor.metrics_store == metrics_store
        assert executor.current_phase == "execution"

    @pytest.mark.asyncio
    async def test_execute_task_async_success(self):
        """Test async task execution success."""
        mock_supervisor = Mock()
        mock_supervisor.decompose_task = Mock(
            return_value=Task(
                task_id="test_task",
                goal="test goal",
                objective="test",
                current_phase="research",
                subtasks=[],
                status="completed",
            )
        )

        agent_pool = AgentPool([])
        executor = MultiAgentExecutor(supervisor=mock_supervisor, agent_pool=agent_pool, max_parallel=2)

        result = await executor.execute_task_async(task_id="task1", description="test task", agent_name="supervisor")

        assert result["success"] is True
        assert "result" in result
        assert "duration" in result
        mock_supervisor.decompose_task.assert_called_once_with("test task")

    @pytest.mark.asyncio
    async def test_execute_task_async_failure(self):
        """Test async task execution with error."""
        mock_supervisor = Mock()
        mock_supervisor.decompose_task = Mock(side_effect=ValueError("Test error"))

        agent_pool = AgentPool([])
        executor = MultiAgentExecutor(supervisor=mock_supervisor, agent_pool=agent_pool, max_parallel=2)

        result = await executor.execute_task_async(task_id="task1", description="test task", agent_name="supervisor")

        assert result["success"] is False
        assert "error" in result
        assert "Test error" in result["error"]
        assert "duration" in result

    @pytest.mark.asyncio
    async def test_execute_tasks_parallel(self):
        """Test parallel task execution with semaphore."""
        mock_supervisor = Mock()
        mock_supervisor.decompose_task = Mock(
            return_value=Task(
                task_id="test_task",
                goal="test goal",
                objective="test",
                current_phase="implementation",
                subtasks=[],
                status="completed",
            )
        )

        agent_pool = AgentPool([])
        executor = MultiAgentExecutor(supervisor=mock_supervisor, agent_pool=agent_pool, max_parallel=2)

        # Create mock tasks
        task1 = Mock(task_id="t1", description="Task 1")
        task2 = Mock(task_id="t2", description="Task 2")
        task3 = Mock(task_id="t3", description="Task 3")

        # Add to queue first
        executor.task_queue.add_task("t1", "Task 1", [])
        executor.task_queue.add_task("t2", "Task 2", [])
        executor.task_queue.add_task("t3", "Task 3", [])

        results = await executor.execute_tasks_parallel([task1, task2, task3], max_concurrent=2)

        # All tasks should complete
        assert len(results) == 3
        assert all(r["success"] for r in results)

        # Verify supervisor was called for each task
        assert mock_supervisor.decompose_task.call_count == 3

    def test_execute_project_simple(self):
        """Test project execution with simple task decomposition."""
        mock_supervisor = Mock()
        mock_supervisor.decompose_task = Mock(
            return_value=Task(
                task_id="main_task",
                goal="Build a CLI tool",
                objective="Build a CLI tool",
                current_phase="implementation",
                subtasks=[
                    SubTask(task_id="sub1", description="Create main.py", assigned_to="supervisor"),
                    SubTask(task_id="sub2", description="Add tests", assigned_to="supervisor"),
                ],
                status="decomposed",
            )
        )

        agent_pool = AgentPool([])
        executor = MultiAgentExecutor(supervisor=mock_supervisor, agent_pool=agent_pool, max_parallel=2)

        result = executor.execute_project("Build a CLI tool")

        # Verify result structure
        assert result["objective"] == "Build a CLI tool"
        assert result["tasks_total"] == 2  # 2 subtasks added
        assert "tasks_completed" in result
        assert "tasks_failed" in result
        assert "iterations" in result
        assert "duration_seconds" in result
        assert "status" in result

    def test_get_progress(self):
        """Test progress reporting."""
        mock_supervisor = Mock()
        agent_pool = AgentPool([])
        executor = MultiAgentExecutor(supervisor=mock_supervisor, agent_pool=agent_pool, max_parallel=2)

        # Add some tasks
        executor.task_queue.add_task("task1", "Test task 1", [])
        executor.task_queue.add_task("task2", "Test task 2", [])

        progress = executor.get_progress()

        assert "queue" in progress
        assert "agent_pool" in progress
        assert "tasks_in_queue" in progress
        assert len(progress["tasks_in_queue"]) == 2
