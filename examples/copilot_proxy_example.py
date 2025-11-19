"""
Example: Using the framework with GitHub Copilot Proxy.

This example demonstrates how to use the Copilot proxy instead of direct OpenAI API.
"""

import os
from autonomy import SupervisorAgent, InterviewerAgent
from tessera.config import FrameworkConfig, LLMConfig
from rich.console import Console
from rich.panel import Panel

console = Console()


def check_copilot_proxy():
    """Check if Copilot proxy is configured and available."""
    base_url = os.getenv("OPENAI_BASE_URL")
    github_token = os.getenv("GITHUB_TOKEN")

    if not base_url:
        console.print("[yellow]⚠ OPENAI_BASE_URL not set - using direct OpenAI API[/yellow]")
        return False

    if not github_token:
        console.print("[yellow]⚠ GITHUB_TOKEN not set - proxy may not work[/yellow]")
        return False

    # Try to ping the proxy
    import requests
    try:
        response = requests.get(f"{base_url.replace('/v1', '')}/health", timeout=2)
        if response.status_code == 200:
            console.print(f"[green]✓ Copilot proxy is running at {base_url}[/green]")
            return True
        else:
            console.print(f"[yellow]⚠ Proxy responded with status {response.status_code}[/yellow]")
            return False
    except requests.exceptions.RequestException as e:
        console.print(f"[red]✗ Cannot reach proxy at {base_url}: {e}[/red]")
        console.print("[yellow]Make sure the proxy is running: docker-compose up -d copilot-proxy[/yellow]")
        return False


def main():
    """Demonstrate using the framework with Copilot proxy."""
    console.print("\n[bold blue]Autonomy Framework - Copilot Proxy Example[/bold blue]\n")

    # Check proxy status
    using_proxy = check_copilot_proxy()

    if not using_proxy:
        console.print("\n[yellow]Run the setup script to configure Copilot proxy:[/yellow]")
        console.print("  ./scripts/setup-copilot-proxy.sh\n")
        return

    console.print()

    # Create configuration (will automatically use proxy if OPENAI_BASE_URL is set)
    config = FrameworkConfig.from_env()

    console.print(Panel(
        f"Provider: {config.llm.provider}\n"
        f"Model: {config.llm.model}\n"
        f"Base URL: {config.llm.base_url or 'Default (OpenAI)'}",
        title="LLM Configuration",
        border_style="cyan"
    ))

    # Example 1: Supervisor with Copilot
    console.print("\n[bold]Example 1: Supervisor Task Decomposition[/bold]\n")

    supervisor = SupervisorAgent(config=config)
    objective = "Build a RESTful API for a todo application with user authentication"

    console.print(f"Objective: {objective}\n")
    console.print("[yellow]Decomposing task via Copilot proxy...[/yellow]\n")

    task = supervisor.decompose_task(objective)

    console.print(Panel(
        f"Goal: {task.goal}\n\n"
        f"Subtasks ({len(task.subtasks)}):\n" +
        "\n".join(f"{i+1}. {st.description}" for i, st in enumerate(task.subtasks)),
        title="Task Breakdown",
        border_style="green"
    ))

    # Example 2: Interviewer with Copilot
    console.print("\n[bold]Example 2: Interview Question Design[/bold]\n")

    interviewer = InterviewerAgent(config=config)
    task_desc = "Design a caching strategy for high-traffic API endpoints"

    console.print(f"Task: {task_desc}\n")
    console.print("[yellow]Generating interview questions via Copilot proxy...[/yellow]\n")

    questions = interviewer.design_interview(task_desc, num_questions=3)

    console.print("[bold]Interview Questions:[/bold]\n")
    for i, q in enumerate(questions, 1):
        console.print(f"{i}. [{q.get('type', 'general')}] {q['text']}")
        console.print(f"   Focus: {q.get('evaluation_focus', 'N/A')}\n")

    # Show cost comparison
    console.print("\n[bold]Cost Comparison:[/bold]")
    console.print(Panel(
        "[green]✓ Using Copilot Proxy[/green]\n"
        "  • Cost: Included with GitHub Copilot subscription\n"
        "  • Model: GPT-4 via Copilot\n"
        "  • Rate Limits: Copilot subscription limits\n\n"
        "[dim]vs. Direct OpenAI API[/dim]\n"
        "  • Cost: ~$0.03 per 1K input tokens, $0.06 per 1K output\n"
        "  • Model: Any OpenAI model\n"
        "  • Rate Limits: Tier-based (higher for paid tiers)",
        title="Cost Analysis",
        border_style="yellow"
    ))

    console.print("\n[bold green]Copilot proxy example completed successfully! ✓[/bold green]\n")


if __name__ == "__main__":
    main()
