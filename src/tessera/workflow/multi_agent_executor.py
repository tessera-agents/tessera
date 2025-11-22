"""
Multi-agent executor for coordinating parallel task execution.
"""

import asyncio
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
    3. Execute tasks in parallel (up to max_parallel) using asyncio
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
        self.current_phase = "execution"

    async def execute_task_async(
        self, task_id: str, description: str, agent_name: str
    ) -> dict[str, Any]:
        """
        Execute a single task asynchronously.

        Args:
            task_id: Unique task identifier
            description: Task description
            agent_name: Agent to execute task

        Returns:
            Task execution result
        """
        start_time = time.time()

        try:
            # Execute task with agent (currently using supervisor for all)
            # In future versions, delegate to specialized agents from pool
            result = await asyncio.to_thread(self.supervisor.decompose_task, description)

            duration = time.time() - start_time

            # Record metrics
            self.metrics_store.record_agent_performance(
                agent_name=agent_name,
                task_id=task_id,
                success=True,
                phase=self.current_phase,
                duration_seconds=duration,
            )

            self.agent_pool.mark_task_complete(agent_name, success=True)

            return {"success": True, "result": result, "duration": duration}

        except Exception as e:
            duration = time.time() - start_time

            # Record failure
            self.metrics_store.record_agent_performance(
                agent_name=agent_name,
                task_id=task_id,
                success=False,
                phase=self.current_phase,
                duration_seconds=duration,
            )

            self.agent_pool.mark_task_complete(agent_name, success=False)

            return {"success": False, "error": str(e), "duration": duration}

    async def execute_tasks_parallel(
        self, tasks: list[Any], max_concurrent: int
    ) -> list[dict[str, Any]]:
        """
        Execute multiple tasks in parallel with concurrency limit.

        Args:
            tasks: List of tasks to execute
            max_concurrent: Maximum concurrent executions

        Returns:
            List of task results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(task: Any) -> dict[str, Any]:
            async with semaphore:
                # Mark task as in progress
                agent_name = "supervisor"  # v1.0: use supervisor for all
                self.task_queue.mark_in_progress(task.task_id, agent_name)

                # Execute task
                result = await self.execute_task_async(task.task_id, task.description, agent_name)

                # Update queue based on result
                if result["success"]:
                    self.task_queue.mark_complete(task.task_id, result=result["result"])
                else:
                    self.task_queue.mark_failed(task.task_id, result["error"])

                return result

        # Execute all tasks concurrently with semaphore limiting parallelism
        results = await asyncio.gather(*[execute_with_semaphore(t) for t in tasks])

        return list(results)

    def execute_project(self, objective: str) -> dict[str, Any]:
        """
        Execute multi-agent project generation with parallel task execution.

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
                dependencies=subtask.dependencies if hasattr(subtask, "dependencies") else [],
            )

        # Step 3: Execute tasks in parallel with iterations
        iteration = 0
        while not self.task_queue.is_complete() and iteration < self.max_iterations:
            iteration += 1

            # Get tasks ready to execute (dependencies satisfied)
            ready_tasks = self.task_queue.get_ready_tasks()

            if not ready_tasks:
                # No tasks ready - check if any in progress
                in_progress_count = sum(
                    1 for t in self.task_queue.tasks.values() if t.status == TaskStatus.IN_PROGRESS
                )

                if in_progress_count == 0 and not self.task_queue.is_complete():
                    # Deadlock: no tasks ready, none in progress, not complete
                    break

                # Wait for in-progress tasks
                time.sleep(0.1)
                continue

            # Execute tasks in parallel (up to max_parallel)
            tasks_to_execute = ready_tasks[: self.max_parallel]

            # Run tasks concurrently using asyncio
            asyncio.run(self.execute_tasks_parallel(tasks_to_execute, self.max_parallel))

        duration = time.time() - start_time

        # Step 4: Return results
        completed_count = sum(
            1 for t in self.task_queue.tasks.values() if t.status == TaskStatus.COMPLETED
        )
        failed_count = sum(
            1 for t in self.task_queue.tasks.values() if t.status == TaskStatus.FAILED
        )

        return {
            "objective": objective,
            "tasks_total": len(self.task_queue.tasks),
            "tasks_completed": completed_count,
            "tasks_failed": failed_count,
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
