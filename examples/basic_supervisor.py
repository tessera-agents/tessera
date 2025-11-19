"""
Example: Basic Supervisor usage for task decomposition and coordination.
"""

import json
from autonomy import SupervisorAgent
from tessera.config import FrameworkConfig
from tessera.models import AgentResponse, TaskStatus
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON

console = Console()


def main():
    """Demonstrate basic Supervisor capabilities."""
    console.print("\n[bold blue]Autonomy Framework - Supervisor Example[/bold blue]\n")

    # Initialize supervisor
    config = FrameworkConfig.from_env()
    supervisor = SupervisorAgent(config=config)

    # Example objective
    objective = """
    Build a web scraping system that extracts product data from e-commerce sites,
    stores it in a database, and generates daily price comparison reports.
    """

    console.print(Panel(objective.strip(), title="Objective", border_style="green"))

    # Decompose task
    console.print("\n[yellow]Decomposing task...[/yellow]\n")
    task = supervisor.decompose_task(objective)

    # Display task breakdown
    console.print(Panel(
        f"Goal: {task.goal}\n\nTask ID: {task.task_id}",
        title="Task Breakdown",
        border_style="blue"
    ))

    console.print("\n[bold]Subtasks:[/bold]")
    for i, subtask in enumerate(task.subtasks, 1):
        console.print(f"\n{i}. [cyan]{subtask.description}[/cyan]")
        console.print(f"   ID: {subtask.task_id}")
        console.print(f"   Acceptance Criteria:")
        for criterion in subtask.acceptance_criteria:
            console.print(f"   - {criterion}")
        if subtask.dependencies:
            console.print(f"   Dependencies: {', '.join(subtask.dependencies)}")

    # Simulate assigning subtasks
    console.print("\n[yellow]Assigning subtasks to agents...[/yellow]\n")
    for subtask in task.subtasks[:2]:  # Assign first 2 for demo
        supervisor.assign_subtask(task.task_id, subtask.task_id, f"agent_{subtask.task_id}")
        console.print(f"✓ Assigned {subtask.task_id} to agent_{subtask.task_id}")

    # Get task status
    console.print("\n[yellow]Current task status:[/yellow]\n")
    status = supervisor.get_task_status(task.task_id)
    console.print(JSON(json.dumps(status, indent=2)))

    # Simulate agent response
    if task.subtasks:
        first_subtask = task.subtasks[0]
        console.print(f"\n[yellow]Simulating response for {first_subtask.task_id}...[/yellow]\n")

        agent_response = AgentResponse(
            agent_name=f"agent_{first_subtask.task_id}",
            task_id=first_subtask.task_id,
            content="I've designed a modular web scraping architecture using Python with Scrapy framework. "
                    "The system will include configurable spiders for different e-commerce sites, "
                    "error handling for rate limits, and proxy rotation for reliability.",
        )

        # Review the response
        review = supervisor.review_agent_output(
            task.task_id,
            first_subtask.task_id,
            agent_response,
        )

        console.print(Panel(
            f"Approved: {review['approved']}\n"
            f"Quality: {review['quality']}\n"
            f"Feedback: {review['feedback']}\n"
            f"Redirect Needed: {review['redirect_needed']}",
            title="Supervisor Review",
            border_style="magenta"
        ))

        # Update status if approved
        if review["approved"]:
            supervisor.update_subtask_status(
                task.task_id,
                first_subtask.task_id,
                TaskStatus.COMPLETED,
                agent_response.content,
            )
            console.print(f"\n✓ Subtask {first_subtask.task_id} marked as COMPLETED")

    # Request interviewer evaluation for a complex subtask
    console.print("\n[yellow]Requesting interviewer evaluation for complex subtask...[/yellow]\n")
    interview_request = supervisor.request_interviewer_evaluation(
        task_description="Build the database schema and ORM layer",
        candidates=["agent_sql_expert", "agent_nosql_specialist", "agent_generalist"],
    )

    console.print(JSON(json.dumps(interview_request, indent=2)))

    console.print("\n[bold green]Supervisor example completed![/bold green]\n")


if __name__ == "__main__":
    main()
