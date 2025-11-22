"""
Tests for workflow components.
"""

import pytest
from unittest.mock import Mock

from tessera.workflow import TaskQueue, TaskStatus, AgentPool, AgentInstance
from tessera.config.schema import AgentDefinition


@pytest.mark.unit
class TestTaskQueue:
    """Test task queue with dependency management."""

    def test_add_task(self):
        """Test adding task to queue."""
        queue = TaskQueue()
        queue.add_task("task-1", "Implement feature")

        assert "task-1" in queue.tasks
        assert queue.tasks["task-1"].description == "Implement feature"
        assert queue.tasks["task-1"].status == TaskStatus.PENDING

    def test_dependency_ordering(self):
        """Test tasks are ordered by dependencies."""
        queue = TaskQueue()
        queue.add_task("task-1", "First task")
        queue.add_task("task-2", "Second task", dependencies=["task-1"])

        # task-1 should come before task-2
        assert queue.execution_order[0] == "task-1"
        assert queue.execution_order[1] == "task-2"

    def test_get_ready_tasks(self):
        """Test getting tasks ready to execute."""
        queue = TaskQueue()
        queue.add_task("task-1", "Independent")
        queue.add_task("task-2", "Depends on 1", dependencies=["task-1"])

        ready = queue.get_ready_tasks()

        # Only task-1 is ready (no dependencies)
        assert len(ready) == 1
        assert ready[0].task_id == "task-1"

    def test_mark_complete_unlocks_dependencies(self):
        """Test completing task makes dependents ready."""
        queue = TaskQueue()
        queue.add_task("task-1", "First")
        queue.add_task("task-2", "Second", dependencies=["task-1"])

        # Initially only task-1 ready
        ready = queue.get_ready_tasks()
        assert len(ready) == 1

        # Complete task-1
        queue.mark_complete("task-1")

        # Now task-2 is ready
        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "task-2"

    def test_status_summary(self):
        """Test queue status summary."""
        queue = TaskQueue()
        queue.add_task("task-1", "One")
        queue.add_task("task-2", "Two")

        queue.mark_complete("task-1")

        summary = queue.get_status_summary()
        assert summary["total"] == 2
        assert summary["completed"] == 1


@pytest.mark.unit
class TestAgentPool:
    """Test agent pool management."""

    def test_load_agents_from_config(self):
        """Test loading agents from config."""
        configs = [
            AgentDefinition(
                name="python-expert",
                model="gpt-4",
                provider="openai",
                capabilities=["python", "coding"]
            ),
        ]

        pool = AgentPool(configs)

        assert "python-expert" in pool.agents
        assert pool.agents["python-expert"].config.model == "gpt-4"

    def test_get_available_agents(self):
        """Test getting available agents."""
        configs = [
            AgentDefinition(name="agent1", model="gpt-4", provider="openai"),
            AgentDefinition(name="agent2", model="gpt-4", provider="openai"),
        ]

        pool = AgentPool(configs)

        # Both available initially
        available = pool.get_available_agents()
        assert len(available) == 2

        # Assign task to one
        pool.agents["agent1"].current_task = "task-1"

        # Only one available now
        available = pool.get_available_agents()
        assert len(available) == 1
        assert available[0].name == "agent2"

    def test_find_best_agent(self):
        """Test best agent selection by capabilities."""
        configs = [
            AgentDefinition(
                name="python-expert",
                model="gpt-4",
                provider="openai",
                capabilities=["python", "testing"]
            ),
            AgentDefinition(
                name="js-expert",
                model="gpt-4",
                provider="openai",
                capabilities=["javascript", "react"]
            ),
        ]

        pool = AgentPool(configs)

        # Find agent for Python task
        agent = pool.find_best_agent(["python"])
        assert agent == "python-expert"

        # Find agent for JS task
        agent = pool.find_best_agent(["javascript"])
        assert agent == "js-expert"
