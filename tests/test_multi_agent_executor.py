"""
Tests for multi-agent executor.
"""

import pytest
from unittest.mock import Mock

from tessera.workflow import MultiAgentExecutor, AgentPool, TaskQueue
from tessera.models import Task, SubTask, TaskStatus


@pytest.mark.unit
class TestMultiAgentExecutor:
    """Test multi-agent executor."""

    def test_initialization(self):
        """Test executor can be initialized."""
        mock_supervisor = Mock()
        agent_pool = AgentPool([])

        executor = MultiAgentExecutor(
            supervisor=mock_supervisor,
            agent_pool=agent_pool,
            max_parallel=3
        )

        assert executor.supervisor == mock_supervisor
        assert executor.max_parallel == 3
        assert isinstance(executor.task_queue, TaskQueue)

    def test_execute_project_creates_task_queue(self):
        """Test project execution creates task queue."""
        mock_supervisor = Mock()
        mock_supervisor.decompose_task.return_value = Task(
            task_id="task-1",
            goal="Test goal",
            subtasks=[
                SubTask(task_id="sub-1", description="First task"),
                SubTask(task_id="sub-2", description="Second task"),
            ]
        )

        agent_pool = AgentPool([])
        executor = MultiAgentExecutor(mock_supervisor, agent_pool)

        result = executor.execute_project("Test objective")

        # Should have decomposed and created queue
        assert result["tasks_total"] == 2
        assert result["objective"] == "Test objective"

    def test_get_progress(self):
        """Test getting execution progress."""
        mock_supervisor = Mock()
        agent_pool = AgentPool([])

        executor = MultiAgentExecutor(mock_supervisor, agent_pool)

        progress = executor.get_progress()

        assert "queue" in progress
        assert "agent_pool" in progress
