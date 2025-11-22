"""
Multi-agent execution logic for CLI.

Separated from main.py for clarity.
"""

from typing import Any

from rich.console import Console

from ..config.schema import TesseraSettings
from ..observability import CostCalculator, MetricsStore
from ..workflow import AgentPool, MultiAgentExecutor


def execute_multi_agent(
    task_description: str,
    settings: TesseraSettings,
    supervisor: Any,
    max_parallel: int,
    metrics_store: MetricsStore,
    cost_calc: CostCalculator,
    console: Console,
) -> dict[str, Any]:
    """
    Execute task using multi-agent coordination.

    Args:
        task_description: Task to execute
        settings: Tessera settings
        supervisor: Supervisor agent instance
        max_parallel: Max parallel agents
        metrics_store: Metrics storage
        cost_calc: Cost calculator
        console: Rich console for output

    Returns:
        Execution result dictionary
    """
    console.print(
        f"[cyan]Multi-agent execution:[/cyan] {len(settings.agents.definitions)} agents, max {max_parallel} parallel\n"
    )

    # Create agent pool from config
    agent_pool = AgentPool(settings.agents.definitions)

    # Create multi-agent executor
    executor = MultiAgentExecutor(
        supervisor=supervisor,
        agent_pool=agent_pool,
        max_parallel=max_parallel,
        metrics_store=metrics_store,
    )

    # Show agent pool status
    pool_status = agent_pool.get_pool_status()
    console.print(f"[dim]Agent pool: {pool_status['total_agents']} agents ready[/dim]")
    for agent_name in agent_pool.agents:
        agent_config = agent_pool.agents[agent_name].config
        console.print(f"[dim]  • {agent_name} ({agent_config.model})[/dim]")
    console.print()

    # Execute project
    console.print("[yellow]Executing with multi-agent coordination...[/yellow]\n")

    result = executor.execute_project(task_description)

    # Display results
    console.print("[green]✓ Multi-agent execution complete![/green]\n")
    console.print("[cyan]Summary:[/cyan]")
    console.print(f"  Tasks: {result['tasks_completed']}/{result['tasks_total']}")
    console.print(f"  Failed: {result['tasks_failed']}")
    console.print(f"  Iterations: {result['iterations']}")
    console.print(f"  Duration: {result['duration_seconds']:.1f}s")
    console.print()

    return result
