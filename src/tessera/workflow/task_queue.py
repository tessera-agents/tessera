"""
Task queue with dependency management for multi-agent execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    READY = "ready"  # Dependencies met, ready to execute
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # Dependencies failed


@dataclass
class QueuedTask:
    """Task in the execution queue."""

    task_id: str
    description: str
    agent_name: str | None = None  # Assigned agent
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[str] = field(default_factory=list)  # Task IDs this depends on
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any | None = None
    error: str | None = None
    retries: int = 0
    max_retries: int = 3


class TaskQueue:
    """
    Manages task queue with dependency resolution.

    Features:
    - Dependency tracking
    - Status management
    - Topological ordering
    - Parallel execution support
    """

    def __init__(self) -> None:
        """Initialize empty task queue."""
        self.tasks: dict[str, QueuedTask] = {}
        self.execution_order: list[str] = []

    def add_task(
        self,
        task_id: str,
        description: str,
        dependencies: list[str] | None = None,
        agent_name: str | None = None,
    ) -> None:
        """
        Add task to queue.

        Args:
            task_id: Unique task identifier
            description: Task description
            dependencies: List of task IDs this task depends on
            agent_name: Optional pre-assigned agent
        """
        task = QueuedTask(
            task_id=task_id,
            description=description,
            dependencies=dependencies or [],
            agent_name=agent_name,
        )

        self.tasks[task_id] = task
        self._update_execution_order()

    def _update_execution_order(self) -> None:
        """
        Update execution order using topological sort.

        Tasks with no dependencies come first, then tasks whose dependencies
        are satisfied, etc.
        """
        # Simple topological sort
        visited: set[str] = set()
        order: list[str] = []

        def visit(task_id: str) -> None:
            if task_id in visited:
                return
            visited.add(task_id)

            task = self.tasks.get(task_id)
            if not task:
                return

            # Visit dependencies first
            for dep_id in task.dependencies:
                visit(dep_id)

            order.append(task_id)

        # Visit all tasks
        for task_id in self.tasks:
            visit(task_id)

        self.execution_order = order

    def get_ready_tasks(self, exclude_in_progress: bool = True) -> list[QueuedTask]:
        """
        Get tasks that are ready to execute.

        A task is ready if:
        - Status is PENDING or READY
        - All dependencies are COMPLETED
        - Not currently IN_PROGRESS (if exclude_in_progress=True)

        Args:
            exclude_in_progress: Don't return tasks already in progress

        Returns:
            List of tasks ready for execution
        """
        ready = []

        for task in self.tasks.values():
            # Skip if wrong status
            if exclude_in_progress and task.status == TaskStatus.IN_PROGRESS:
                continue

            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED):
                continue

            # Check if all dependencies are met
            dependencies_met = all(
                self.tasks.get(dep_id, QueuedTask(task_id="", description="")).status
                == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )

            if dependencies_met:
                ready.append(task)

        return ready

    def mark_in_progress(self, task_id: str, agent_name: str) -> None:
        """
        Mark task as in progress.

        Args:
            task_id: Task identifier
            agent_name: Agent assigned to this task
        """
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.IN_PROGRESS
            self.tasks[task_id].agent_name = agent_name
            self.tasks[task_id].started_at = datetime.now()

    def mark_complete(self, task_id: str, result: Any | None = None) -> None:
        """
        Mark task as completed.

        Args:
            task_id: Task identifier
            result: Optional task result
        """
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            self.tasks[task_id].completed_at = datetime.now()
            self.tasks[task_id].result = result

    def mark_failed(self, task_id: str, error: str) -> None:
        """
        Mark task as failed.

        Args:
            task_id: Task identifier
            error: Error message
        """
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.FAILED
            self.tasks[task_id].error = error
            self.tasks[task_id].completed_at = datetime.now()
            self.tasks[task_id].retries += 1

    def get_task(self, task_id: str) -> QueuedTask | None:
        """Get task by ID."""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> list[QueuedTask]:
        """Get all tasks in execution order."""
        return [self.tasks[task_id] for task_id in self.execution_order if task_id in self.tasks]

    def get_status_summary(self) -> dict[str, int]:
        """
        Get summary of task statuses.

        Returns:
            Dict with counts for each status
        """
        summary = {
            "total": len(self.tasks),
            "pending": 0,
            "ready": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
            "blocked": 0,
        }

        for task in self.tasks.values():
            summary[task.status.value] += 1

        # Calculate ready tasks
        summary["ready"] = len(self.get_ready_tasks(exclude_in_progress=True))

        return summary

    def is_complete(self) -> bool:
        """Check if all tasks are complete."""
        return all(
            task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED)
            for task in self.tasks.values()
        )

    def has_failures(self) -> bool:
        """Check if any tasks failed."""
        return any(task.status == TaskStatus.FAILED for task in self.tasks.values())
