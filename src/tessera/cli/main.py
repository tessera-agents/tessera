"""
from rich.panel import Panel
Tessera CLI main entry point.

Usage:
    # With uvx (package name: tessera-agents)
    uvx tessera-agents                    # Interactive mode
    uvx tessera-agents "Build a web scraper"  # Direct task

    # After installation (uv tool install tessera-agents)
    tessera                    # Interactive mode
    tessera "Build a web scraper"  # Direct task
    tessera --help             # Show help
"""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from tessera.config.schema import TesseraSettings
from tessera.config.xdg import ensure_directories, get_config_file_path

app = typer.Typer(
    name="tessera",
    help="No-code multi-agent AI orchestration for full project generation",
    add_completion=False,
)

console = Console()


def load_config(custom_path: str | None = None) -> TesseraSettings:
    """
    Load Tessera configuration from YAML + env vars.

    Args:
        custom_path: Optional custom config file path (overrides XDG lookup)

    Returns:
        TesseraSettings instance
    """
    if custom_path:
        config_file = Path(custom_path)
        if not config_file.exists():
            console.print(f"[red]Config file not found:[/red] {config_file}\n")
            raise typer.Exit(2)
    else:
        config_file = get_config_file_path()
        if not config_file.exists():
            console.print(f"[yellow]No config file found at {config_file}[/yellow]")
            console.print("Run [cyan]tessera init[/cyan] to create one.\n")

    # Load settings (XDGYamlSettingsSource will pick up the file)
    try:
        return TesseraSettings()
    except (ValueError, OSError, RuntimeError) as e:
        console.print(f"[red]Error loading configuration:[/red] {e}")
        console.print("\nUsing default configuration.\n")
        return TesseraSettings()


@app.command()
def main(  # noqa: PLR0913
    task: Annotated[str, typer.Argument(help="Task description. If not provided, starts interactive mode.")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show plan without executing")] = False,
    background: Annotated[bool, typer.Option("--background", "-b", help="Run in background mode")] = False,
    multi_agent: Annotated[
        bool, typer.Option("--multi-agent", "-m", help="Use multi-agent execution (v0.3.0)")
    ] = False,
    max_parallel: Annotated[int, typer.Option("--max-parallel", help="Max parallel agents")] = 3,
    config_file: Annotated[str, typer.Option("--config", "-c", help="Custom config file path")] = "",
) -> None:
    """
    Main entry point for Tessera.

    Examples:
        tessera
        tessera "Build a web scraper"
        tessera --dry-run "Deploy application"
        tessera --background "Generate full project"
    """
    from .commands.main_cmd import execute_main

    settings = load_config(config_file if config_file else None)
    execute_main(
        task=task,
        dry_run=dry_run,
        background=background,
        multi_agent=multi_agent,
        max_parallel=max_parallel,
        config_file=config_file,
        settings=settings,
        console=console,
    )


@app.command()
def init() -> None:
    """Initialize Tessera configuration with interactive wizard."""
    console.print(
        Panel.fit(
            "[bold cyan]Tessera Configuration Wizard[/bold cyan]\n[dim]Setting up ~/.config/tessera/config.yaml[/dim]",
            border_style="cyan",
        )
    )

    config_file = get_config_file_path()

    # Check if config already exists
    if config_file.exists():
        overwrite = Confirm.ask(
            f"\n[yellow]Config file already exists at {config_file}[/yellow]\nOverwrite it?",
            default=False,
        )
        if not overwrite:
            console.print("\n[green]Keeping existing configuration.[/green]\n")
            return

    console.print("\n[cyan]Let's set up Tessera![/cyan]\n")

    # Ask essential questions (things without sane defaults)

    # 1. LLM Provider
    provider = Prompt.ask(
        "Which LLM provider will you use",
        choices=["openai", "anthropic", "ollama", "other"],
        default="openai",
    )

    # 2. API Key (if not local)
    api_key_env = ""
    if provider != "ollama":
        console.print(f"\n[dim]You'll need an API key for {provider}.[/dim]")
        has_key = Confirm.ask(f"Do you have a {provider.upper()}_API_KEY environment variable set?", default=True)

        if has_key:
            api_key_env = f"{provider.upper()}_API_KEY"
        else:
            console.print(f"\n[yellow]Please set {provider.upper()}_API_KEY in your environment:[/yellow]")
            console.print(f"  export {provider.upper()}_API_KEY=your-key-here\n")

    # 3. Default model
    default_models = {
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20241022",
        "ollama": "llama3.2",
    }
    model = Prompt.ask("Default model to use", default=default_models.get(provider, "gpt-4o"))

    # 4. Daily cost limit
    daily_limit = Prompt.ask("Daily cost limit in USD (soft limit, just warnings)", default="10.00")

    # Ensure directories exist
    dirs = ensure_directories()

    # Create minimal config from template
    import shutil
    from pathlib import Path

    template_path = Path(__file__).parent.parent / "config" / "defaults.yaml"

    # Copy template
    shutil.copy(template_path, config_file)

    # Update with user choices (simple replacement for v0.1)
    with Path(config_file).open() as f:
        config_content = f.read()

    config_content = config_content.replace('provider: "openai"', f'provider: "{provider}"')
    config_content = config_content.replace('model: "gpt-4"', f'model: "{model}"')
    config_content = config_content.replace("daily_usd: 10.00", f"daily_usd: {daily_limit}")

    with Path(config_file).open("w") as f:
        f.write(config_content)

    # Create default supervisor prompt
    supervisor_prompt_file = dirs["config_prompts"] / "supervisor.md"
    if not supervisor_prompt_file.exists():
        from tessera.legacy_config import SUPERVISOR_PROMPT

        supervisor_prompt_file.write_text(SUPERVISOR_PROMPT)

    console.print("\n[green]✓[/green] Configuration created successfully!")
    console.print(f"\n[cyan]Config file:[/cyan] {config_file}")
    console.print(f"[cyan]Prompts directory:[/cyan] {dirs['config_prompts']}")
    console.print(f"[cyan]Cache directory:[/cyan] {dirs['cache']}\n")

    console.print("[yellow]Next steps:[/yellow]")
    console.print(f"  1. Review config: [dim]{config_file}[/dim]")
    console.print(f"  2. Set API key: [dim]export {api_key_env or 'YOUR_PROVIDER'}_API_KEY=...[/dim]")
    console.print("  3. Run Tessera: [dim]tessera[/dim]\n")

    # Test config load
    try:
        TesseraSettings()
        console.print("[green]✓[/green] Configuration validated successfully!\n")
    except (ValueError, OSError, RuntimeError) as e:
        console.print(f"[red]Warning:[/red] Config validation failed: {e}\n")


@app.command()
def workflow_list() -> None:
    """List available workflow templates."""
    from ..workflow.templates import WorkflowTemplateStorage

    storage = WorkflowTemplateStorage()
    templates = storage.list_templates()

    if not templates:
        console.print("[yellow]No workflow templates found.[/yellow]\n")
        console.print("Install built-in templates: [cyan]tessera workflow install-builtins[/cyan]\n")
        return

    console.print("[cyan]Available Workflow Templates:[/cyan]\n")

    for template_name in templates:
        info = storage.get_template_info(template_name)
        if info:
            console.print(f"• [green]{info['name']}[/green]")
            console.print(f"  {info['description']}")
            console.print(f"  [dim]Phases: {info['phase_count']}, Agents: {info['agent_count']}[/dim]\n")


@app.command()
def workflow_show(name: str) -> None:
    """Show details of a workflow template."""
    from ..workflow.templates import WorkflowTemplateStorage

    storage = WorkflowTemplateStorage()
    template = storage.load(name)

    if template is None:
        console.print(f"[red]Template not found:[/red] {name}\n")
        return

    console.print(f"[cyan]{template.name}[/cyan]")
    console.print(f"{template.description}\n")
    console.print(f"[dim]Complexity: {template.complexity}[/dim]")
    console.print(f"[dim]Phases: {len(template.phases)}[/dim]\n")

    console.print("[cyan]Phases:[/cyan]")
    for phase in template.phases:
        console.print(f"  • {phase.name}: {phase.description}")

    if template.suggested_agents:
        console.print("\n[cyan]Suggested Agents:[/cyan]")
        for agent in template.suggested_agents:
            console.print(f"  • {agent['name']} ({agent['model']})")


@app.command()
def workflow_install_builtins() -> None:
    """Install built-in workflow templates."""
    from ..workflow.templates import install_builtin_templates

    count = install_builtin_templates()

    console.print(f"[green]✓[/green] Installed {count} built-in templates\n")
    console.print("List templates: [cyan]tessera workflow list[/cyan]\n")


@app.command()
def session_list() -> None:
    """List all execution sessions."""
    from ..api.session import get_session_manager

    manager = get_session_manager()
    sessions = manager.list_sessions()

    if not sessions:
        console.print("[yellow]No sessions found.[/yellow]\n")
        return

    console.print("[cyan]Execution Sessions:[/cyan]\n")

    for session in sessions:
        status_color = {
            "created": "yellow",
            "running": "green",
            "paused": "yellow",
            "completed": "green",
            "failed": "red",
            "cancelled": "dim",
        }.get(session.status.value, "white")

        console.print(f"• [{status_color}]{session.session_id[:8]}...[/{status_color}] - {session.objective}")
        console.print(f"  Status: [{status_color}]{session.status.value}[/{status_color}]")
        console.print(f"  Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")


@app.command()
def session_attach(session_id: str) -> None:
    """Attach to and monitor a session."""
    from ..api.session import get_session_manager

    manager = get_session_manager()
    session = manager.get_session(session_id)

    if session is None:
        console.print(f"[red]Session not found:[/red] {session_id}\n")
        raise typer.Exit(1)

    console.print(f"[cyan]Session {session_id[:8]}...[/cyan]")
    console.print(f"Objective: {session.objective}")
    console.print(f"Status: {session.status.value}\n")

    # Display session details
    if session.tasks:
        console.print(f"[cyan]Tasks:[/cyan] {len(session.tasks)}")


@app.command()
def session_pause(session_id: str) -> None:
    """Pause a running session."""
    from ..api.session import get_session_manager

    manager = get_session_manager()
    success = manager.pause_session(session_id)

    if not success:
        console.print(f"[red]Failed to pause session:[/red] {session_id}\n")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Session paused: {session_id}\n")


@app.command()
def session_resume(session_id: str) -> None:
    """Resume a paused session."""
    from ..api.session import get_session_manager

    manager = get_session_manager()
    success = manager.resume_session(session_id)

    if not success:
        console.print(f"[red]Failed to resume session:[/red] {session_id}\n")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Session resumed: {session_id}\n")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start Tessera API server."""
    from ..api.server import start_server

    console.print("[cyan]Starting Tessera API server...[/cyan]")
    console.print(f"Listening on http://{host}:{port}\n")

    start_server(host=host, port=port)


@app.command()
def workspace_list() -> None:
    """List all workspaces."""
    from ..workspace import get_workspace_manager

    manager = get_workspace_manager()
    workspaces = manager.list_workspaces(include_archived=False)

    if not workspaces:
        console.print("[yellow]No workspaces found.[/yellow]\n")
        console.print("Create one: [cyan]tessera workspace register <name> <path>[/cyan]\n")
        return

    console.print("[cyan]Workspaces:[/cyan]\n")

    for ws in workspaces:
        status = "[dim](archived)[/dim]" if ws.archived else ""
        console.print(f"• [green]{ws.name}[/green] {status}")
        console.print(f"  Path: {ws.path}")
        console.print(f"  Last accessed: {ws.last_accessed.strftime('%Y-%m-%d %H:%M:%S')}\n")


@app.command()
def workspace_register(name: str, path: str) -> None:
    """Register a new workspace."""
    from ..workspace import get_workspace_manager

    manager = get_workspace_manager()
    workspace = manager.register_workspace(name, Path(path))

    console.print(f"[green]✓[/green] Registered workspace: {name}")
    console.print(f"Path: {workspace.path}\n")


@app.command()
def workspace_enter(name: str) -> None:
    """Enter a workspace (change directory)."""
    from ..workspace import get_workspace_manager

    manager = get_workspace_manager()
    success = manager.enter_workspace(name)

    if not success:
        console.print(f"[red]Failed to enter workspace:[/red] {name}\n")
        raise typer.Exit(1)

    workspace = manager.get_workspace(name)
    if not workspace:
        console.print(f"[red]Workspace not found:[/red] {name}\n")
        raise typer.Exit(1)
    console.print(f"[green]✓[/green] Entered workspace: {name}")
    console.print(f"Working directory: {workspace.path}\n")


@app.command()
def workspace_archive(name: str) -> None:
    """Archive a workspace."""
    from ..workspace import get_workspace_manager

    manager = get_workspace_manager()
    success = manager.archive_workspace(name)

    if not success:
        console.print(f"[red]Failed to archive workspace:[/red] {name}\n")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Archived workspace: {name}\n")


@app.command()
def workspace_unarchive(name: str) -> None:
    """Unarchive a workspace."""
    from ..workspace import get_workspace_manager

    manager = get_workspace_manager()
    success = manager.unarchive_workspace(name)

    if not success:
        console.print(f"[red]Failed to unarchive workspace:[/red] {name}\n")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Unarchived workspace: {name}\n")


@app.command()
def version() -> None:
    """Show Tessera version information."""
    console.print("[cyan]Tessera v0.5.0[/cyan]")
    console.print("[dim]Multi-Agent Orchestration Framework[/dim]\n")


if __name__ == "__main__":
    app()
