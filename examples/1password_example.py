#!/usr/bin/env python3
"""
Example demonstrating 1Password integration for secure secret management.

This example shows how to:
1. Check if 1Password CLI is available
2. Retrieve GitHub token from 1Password
3. Use the token with the autonomy framework
4. Fall back to environment variables if 1Password unavailable
"""

from tessera.secrets import SecretManager, check_secrets_available
from autonomy import SupervisorAgent
from tessera.config import LLMConfig
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def main():
    """Demonstrate 1Password integration."""

    console.print("\n[bold cyan]1Password Integration Example[/bold cyan]\n")

    # Step 1: Check 1Password availability
    console.print("[yellow]Step 1: Checking 1Password CLI availability...[/yellow]")
    is_available = SecretManager.check_1password_available()

    if is_available:
        console.print("[green]✓ 1Password CLI is available and authenticated[/green]")
    else:
        console.print("[red]✗ 1Password CLI not available[/red]")
        console.print("[yellow]  Will fall back to environment variables[/yellow]")

    # Step 2: Check which secrets are available
    console.print("\n[yellow]Step 2: Checking available secrets...[/yellow]")
    secrets_status = check_secrets_available()

    table = Table(title="Secret Availability")
    table.add_column("Secret", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Source", style="yellow")

    for secret_name, is_available in secrets_status.items():
        status = "✓ Available" if is_available else "✗ Not Found"

        # Determine source
        if is_available:
            if SecretManager.check_1password_available():
                source = "1Password CLI"
            else:
                source = "Environment Variable"
        else:
            source = "Not Set"

        table.add_row(secret_name, status, source)

    console.print(table)

    # Step 3: Get GitHub token
    console.print("\n[yellow]Step 3: Retrieving GitHub token...[/yellow]")
    github_token = SecretManager.get_github_token()

    if github_token:
        console.print(f"[green]✓ GitHub token retrieved[/green]")
        console.print(f"  Token preview: {github_token[:10]}{'*' * 20}")

        # Show source
        if SecretManager.get_from_1password("GitHub Copilot", "token"):
            console.print("  Source: [cyan]1Password CLI[/cyan]")
        else:
            console.print("  Source: [yellow]Environment Variable[/yellow]")
    else:
        console.print("[red]✗ GitHub token not found[/red]")
        console.print("\n[yellow]Please set up your token using one of:[/yellow]")
        console.print("  1. Run: ./scripts/setup-1password.sh")
        console.print("  2. Set GITHUB_TOKEN in .env file")
        return

    # Step 4: Create supervisor using the token
    console.print("\n[yellow]Step 4: Creating supervisor agent...[/yellow]")

    try:
        # The framework automatically uses SecretManager to get the token
        config = LLMConfig.from_env(provider="openai")
        supervisor = SupervisorAgent(config=config)

        console.print("[green]✓ Supervisor created successfully[/green]")
        console.print(f"  Provider: {config.provider}")
        console.print(f"  Model: {config.model}")
        if config.base_url:
            console.print(f"  Base URL: {config.base_url}")
            console.print("  [cyan]Using GitHub Copilot proxy[/cyan]")

        # Step 5: Test with a simple task
        console.print("\n[yellow]Step 5: Testing with a simple task...[/yellow]")

        task = supervisor.decompose_task(
            "Create a simple Python script that reads a CSV file and prints statistics"
        )

        console.print("[green]✓ Task decomposition successful[/green]")
        console.print(f"\n[bold]Goal:[/bold] {task.goal}")
        console.print(f"\n[bold]Subtasks ({len(task.subtasks)}):[/bold]")

        for i, subtask in enumerate(task.subtasks, 1):
            console.print(f"  {i}. {subtask.description}")
            if subtask.acceptance_criteria:
                console.print(f"     [dim]Criteria: {', '.join(subtask.acceptance_criteria[:2])}...[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Error creating supervisor: {e}[/red]")
        return

    # Step 6: Show security benefits
    console.print("\n[yellow]Step 6: Security Benefits[/yellow]")

    benefits = Panel(
        "[green]✓[/green] Secrets encrypted in 1Password vault\n"
        "[green]✓[/green] No plaintext API keys in .env files\n"
        "[green]✓[/green] Centralized secret management\n"
        "[green]✓[/green] Automatic fallback to environment variables\n"
        "[green]✓[/green] Team-friendly secret sharing\n"
        "[green]✓[/green] Audit trail for secret access",
        title="[bold cyan]1Password Security Benefits[/bold cyan]",
        border_style="cyan"
    )
    console.print(benefits)

    # Step 7: Show how to update token
    console.print("\n[yellow]Step 7: How to Update Token[/yellow]")

    update_panel = Panel(
        "[bold]Update token in 1Password:[/bold]\n"
        "  op item edit 'GitHub Copilot' token='new_token_here'\n\n"
        "[bold]Update token in environment:[/bold]\n"
        "  Edit .env file and set GITHUB_TOKEN=new_token\n\n"
        "[bold]Verify token:[/bold]\n"
        "  op item get 'GitHub Copilot' --fields token",
        title="[bold cyan]Token Management[/bold cyan]",
        border_style="cyan"
    )
    console.print(update_panel)

    console.print("\n[bold green]1Password integration example complete![/bold green]\n")


if __name__ == "__main__":
    main()
