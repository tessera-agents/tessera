"""
Real-time progress display for multi-agent execution.

Provides live updates on task execution status using Rich progress bars.
"""

from typing import Any

from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.table import Table

from .task_queue import TaskQueue, TaskStatus
from .agent_pool import AgentPool


class ProgressDisplay:
    """
    Real-time progress display for multi-agent execution.

    Shows:
    - Overall progress bar
    - Per-agent status
    - Task queue summary
    - Current phase
    """

    def __init__(self, console: Console | None = None) -> None:
        """
        Initialize progress display.

        Args:
            console: Rich console instance
        """
        self.console = console or Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
        )
        self.task_ids: dict[str, TaskID] = {}

    def create_task_progress(self, name: str, total: int) -> TaskID:
        """
        Create a progress task.

        Args:
            name: Task name/description
            total: Total units of work

        Returns:
            TaskID for updating progress
        """
        task_id = self.progress.add_task(name, total=total)
        self.task_ids[name] = task_id
        return task_id

    def update_progress(self, name: str, advance: int = 1) -> None:
        """
        Update progress for a task.

        Args:
            name: Task name
            advance: Amount to advance
        """
        if name in self.task_ids:
            self.progress.update(self.task_ids[name], advance=advance)

    def generate_status_table(
        self, task_queue: TaskQueue, agent_pool: AgentPool, current_phase: str
    ) -> Table:
        """
        Generate status table for display.

        Args:
            task_queue: Current task queue
            agent_pool: Current agent pool
            current_phase: Current execution phase

        Returns:
            Rich table with status
        """
        table = Table(title=f"Execution Status - Phase: {current_phase}")

        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        # Task queue stats
        queue_status = task_queue.get_status_summary()
        table.add_row("Total Tasks", str(queue_status["total"]))
        table.add_row("Completed", str(queue_status["completed"]))
        table.add_row("In Progress", str(queue_status["in_progress"]))
        table.add_row("Failed", str(queue_status["failed"]))
        table.add_row("Pending", str(queue_status["pending"]))

        # Agent pool stats
        pool_status = agent_pool.get_pool_status()
        table.add_row("Available Agents", str(pool_status["available_agents"]))
        table.add_row("Busy Agents", str(pool_status["busy_agents"]))

        return table

    def display_live(
        self, task_queue: TaskQueue, agent_pool: AgentPool, current_phase: str
    ) -> Live:
        """
        Create live display context manager.

        Args:
            task_queue: Task queue to monitor
            agent_pool: Agent pool to monitor
            current_phase: Current phase name

        Returns:
            Live display context
        """
        table = self.generate_status_table(task_queue, agent_pool, current_phase)
        return Live(table, console=self.console, refresh_per_second=4)


def create_progress_display() -> ProgressDisplay:
    """
    Create default progress display.

    Returns:
        Configured ProgressDisplay instance
    """
    return ProgressDisplay()
