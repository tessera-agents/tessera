"""
Multi-agent executor for coordinating parallel task execution.
"""

import time
from typing import Any

from ..observability import MetricsStore
from .agent_pool import AgentPool
from .task_queue import TaskQueue, TaskStatus


class MultiAgentExecutor:
    """
    Orchestrates multiple agents working on tasks concurrently.

    Workflow:
    1. Supervisor decomposes objective into tasks
    2. Tasks added to queue with dependencies
    3. Execute tasks in parallel (up to max_parallel)
    4. Monitor progress, handle failures
    5. Return when all complete or max_iterations reached
    """

    def __init__(
        self,
        supervisor: Any,
        agent_pool: AgentPool,
        max_parallel: int = 3,
        max_iterations: int = 10,
        metrics_store: MetricsStore | None = None,
    ) -> None:
        """
        Initialize multi-agent executor.

        Args:
            supervisor: Supervisor agent instance
            agent_pool: Pool of available agents
            max_parallel: Maximum agents running concurrently
            max_iterations: Maximum execution loop iterations
            metrics_store: Optional metrics storage
        """
        self.supervisor = supervisor
        self.agent_pool = agent_pool
        self.max_parallel = max_parallel
        self.max_iterations = max_iterations
        self.metrics_store = metrics_store or MetricsStore()

        self.task_queue = TaskQueue()
        self.current_phase = "execution"  # For v0.2, hardcode to execution

    def execute_project(self, objective: str) -> dict[str, Any]:
        """
        Execute multi-agent project generation.

        Args:
            objective: High-level objective to accomplish

        Returns:
            Dict with execution results and metadata
        """
        start_time = time.time()

        # Step 1: Supervisor decomposes objective
        decomposed = self.supervisor.decompose_task(objective)

        # Step 2: Create task queue from subtasks
        for subtask in decomposed.subtasks:
            self.task_queue.add_task(
                task_id=subtask.task_id,
                description=subtask.description,
                dependencies=subtask.dependencies,
            )

        # Step 3: Execute tasks
        iteration = 0
        while not self.task_queue.is_complete() and iteration < self.max_iterations:
            iteration += 1

            # Get tasks ready to execute
            ready_tasks = self.task_queue.get_ready_tasks()

            if not ready_tasks:
                # No tasks ready - either waiting on dependencies or all done
                if self.task_queue.is_complete():
                    break
                # Wait a bit for in-progress tasks
                time.sleep(0.5)
                continue

            # Execute up to max_parallel tasks
            tasks_to_execute = ready_tasks[: self.max_parallel]

            for task in tasks_to_execute:
                # Find best agent for this task
                # Find best agent for this task
                # For v0.2, use supervisor for all tasks
                # v0.3 will add capability matching
                agent_name = "supervisor"

                # Assign task
                self.task_queue.mark_in_progress(task.task_id, agent_name)

                # Actually execute the task with supervisor
                try:
                    # For v0.2: supervisor re-processes each subtask
                    # v0.3 will delegate to specialized agents
                    subtask_result = self.supervisor.decompose_task(task.description)

                    self.task_queue.mark_complete(task.task_id, result=subtask_result)

                    # Track success
                    self.agent_pool.mark_task_complete(agent_name, success=True)

                except Exception as e:
                    # Mark failed
                    self.task_queue.mark_failed(task.task_id, str(e))
                    self.agent_pool.mark_task_complete(agent_name, success=False)

                # Record metrics
                self.metrics_store.record_agent_performance(
                    agent_name=agent_name,
                    task_id=task.task_id,
                    success=True,
                    phase=self.current_phase,
                )

        duration = time.time() - start_time

        # Step 4: Return results
        return {
            "objective": objective,
            "tasks_total": len(self.task_queue.tasks),
            "tasks_completed": sum(
                1 for t in self.task_queue.tasks.values() if t.status == TaskStatus.COMPLETED
            ),
            "tasks_failed": sum(
                1 for t in self.task_queue.tasks.values() if t.status == TaskStatus.FAILED
            ),
            "iterations": iteration,
            "duration_seconds": duration,
            "status": "completed" if self.task_queue.is_complete() else "incomplete",
        }

    def get_progress(self) -> dict[str, Any]:
        """
        Get current execution progress.

        Returns:
            Dict with progress information
        """
        queue_status = self.task_queue.get_status_summary()
        pool_status = self.agent_pool.get_pool_status()

        return {
            "queue": queue_status,
            "agent_pool": pool_status,
            "tasks_in_queue": self.task_queue.get_all_tasks(),
        }
