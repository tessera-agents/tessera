"""Extended tests for task queue."""

import pytest

from tessera.workflow.task_queue import TaskQueue, TaskStatus


@pytest.mark.unit
class TestTaskQueueExtended:
    """Extended task queue tests for coverage."""

    def test_mark_failed(self):
        """Test marking task as failed."""
        queue = TaskQueue()
        queue.add_task("task1", "Test task", [])

        queue.mark_failed("task1", "Error message")

        task = queue.tasks["task1"]
        assert task.status == TaskStatus.FAILED
        assert task.error == "Error message"
        assert task.completed_at is not None

    def test_get_task(self):
        """Test getting specific task."""
        queue = TaskQueue()
        queue.add_task("task1", "Test task", [])

        task = queue.get_task("task1")

        assert task is not None
        assert task.task_id == "task1"
        assert task.description == "Test task"

    def test_get_task_not_found(self):
        """Test getting non-existent task."""
        queue = TaskQueue()

        task = queue.get_task("nonexistent")

        assert task is None

    def test_has_failures(self):
        """Test checking for failures."""
        queue = TaskQueue()
        queue.add_task("task1", "Task 1", [])
        queue.add_task("task2", "Task 2", [])

        # No failures initially
        assert queue.has_failures() is False

        # Mark one failed
        queue.mark_failed("task1", "Error")

        assert queue.has_failures() is True

    def test_get_status_summary(self):
        """Test status summary generation."""
        queue = TaskQueue()
        queue.add_task("task1", "Task 1", [])
        queue.add_task("task2", "Task 2", [])
        queue.add_task("task3", "Task 3", [])

        queue.mark_in_progress("task1", "agent1")
        queue.mark_complete("task2")

        summary = queue.get_status_summary()

        assert summary["total"] == 3
        assert summary["pending"] == 1
        assert summary["in_progress"] == 1
        assert summary["completed"] == 1
        assert summary["failed"] == 0
        assert summary["blocked"] == 0

    def test_is_complete_true(self):
        """Test queue completion check when all done."""
        queue = TaskQueue()
        queue.add_task("task1", "Task 1", [])
        queue.add_task("task2", "Task 2", [])

        queue.mark_complete("task1")
        queue.mark_complete("task2")

        assert queue.is_complete() is True

    def test_is_complete_false(self):
        """Test queue completion with pending tasks."""
        queue = TaskQueue()
        queue.add_task("task1", "Task 1", [])

        assert queue.is_complete() is False

    def test_get_all_tasks(self):
        """Test getting all tasks."""
        queue = TaskQueue()
        queue.add_task("task1", "Task 1", [])
        queue.add_task("task2", "Task 2", [])

        all_tasks = queue.get_all_tasks()

        assert len(all_tasks) == 2
        assert any(t.task_id == "task1" for t in all_tasks)
        assert any(t.task_id == "task2" for t in all_tasks)

    def test_complex_dependency_chain(self):
        """Test complex task dependencies."""
        queue = TaskQueue()

        # Create dependency chain: task3 -> task2 -> task1
        queue.add_task("task1", "Base task", [])
        queue.add_task("task2", "Middle task", dependencies=["task1"])
        queue.add_task("task3", "Final task", dependencies=["task2"])

        # Initially only task1 is ready
        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "task1"

        # Complete task1, task2 becomes ready
        queue.mark_complete("task1")
        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "task2"

        # Complete task2, task3 becomes ready
        queue.mark_complete("task2")
        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "task3"
