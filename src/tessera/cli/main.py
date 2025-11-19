"""
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

import os
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from typing_extensions import Annotated
from typing import Optional
from pathlib import Path

from ..config.schema import TesseraSettings
from ..config.xdg import ensure_directories, get_config_file_path
from ..observability import init_tracer, MetricsStore, CostCalculator, TokenUsageCallback
from ..workflow import PhaseExecutor

app = typer.Typer(
    name="tessera",
    help="No-code multi-agent AI orchestration for full project generation",
    add_completion=False,
)

console = Console()


def load_config(custom_path: Optional[str] = None) -> TesseraSettings:
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
        settings = TesseraSettings()
        return settings
    except Exception as e:
        console.print(f"[red]Error loading configuration:[/red] {e}")
        console.print("\nUsing default configuration.\n")
        return TesseraSettings()


@app.command()
def main(
    task: Annotated[
        str,
        typer.Argument(
            help="Task description. If not provided, starts interactive mode."
        )
    ] = "",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show plan without executing")
    ] = False,
    background: Annotated[
        bool,
        typer.Option("--background", "-b", help="Run in background mode")
    ] = False,
    multi_agent: Annotated[
        bool,
        typer.Option("--multi-agent", "-m", help="Use multi-agent execution (v0.2.0)")
    ] = False,
    max_parallel: Annotated[
        int,
        typer.Option("--max-parallel", help="Max parallel agents")
    ] = 3,
    config_file: Annotated[
        str,
        typer.Option("--config", "-c", help="Custom config file path")
    ] = "",
):
    """
    Main entry point for Tessera.

    Examples:
        tessera
        tessera "Build a web scraper"
        tessera --dry-run "Deploy application"
        tessera --background "Generate full project"
    """
    console.print(
        Panel.fit(
            "[bold cyan]TESSERA[/bold cyan]\n"
            "Multi-Agent Orchestration Framework\n"
            "[dim]v0.1.0 - Foundation Release[/dim]",
            border_style="cyan",
        )
    )

    # Ensure directories exist
    dirs = ensure_directories()
    console.print(f"[dim]Config: {dirs['config']}[/dim]\n")

    # Load configuration
    try:
        settings = load_config(config_file if config_file else None)
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}\n")
        raise typer.Exit(2)

    # Initialize observability
    init_tracer(app_name="tessera", export_to_file=settings.observability.local.enabled)
    metrics_store = MetricsStore()
    cost_calc = CostCalculator()

    # Get task description
    if not task:
        # Interactive mode
        console.print("[cyan]Interactive Mode[/cyan]\n")
        task = Prompt.ask("? What would you like to build")

        if not task.strip():
            console.print("[red]No task provided.[/red]\n")
            raise typer.Exit(1)

        complexity = Prompt.ask(
            "? Complexity level",
            choices=["simple", "medium", "complex"],
            default=settings.tessera.default_complexity,
        )

        use_interview = Confirm.ask(
            "? Interview mode (recommended for better results)",
            default=settings.project_generation.interview.enabled,
        )

        console.print()

    # Execute task
    console.print(f"[green]Task:[/green] {task}\n")

    if dry_run:
        console.print("[yellow]Dry-run mode:[/yellow] Planning only (no execution)\n")

    if background:
        console.print("[yellow]Background mode not yet implemented.[/yellow]")
        console.print("Coming in v0.5.0!\n")
        raise typer.Exit(1)

    # Check if multi-agent mode should be used
    # Auto-enable if config has multiple agents
    use_multi_agent = multi_agent or len(settings.agents.definitions) > 1

    if use_multi_agent and len(settings.agents.definitions) > 1:
        console.print(f"[cyan]Multi-agent mode:[/cyan] {len(settings.agents.definitions)} agents\n")
    else:
        use_multi_agent = False  # Force single-agent if not enough agents

    # Execute task with supervisor (or multi-agent executor)
    try:
        from ..observability.tracer import get_tracer, set_span_attributes
        from ..supervisor import SupervisorAgent
        from ..legacy_config import LLMConfig
        import uuid
        import time

        task_id = f"task-{uuid.uuid4().hex[:8]}"
        tracer = get_tracer()
        start_time = time.time()

        with tracer.start_as_current_span("tessera_task_execution") as span:
            set_span_attributes(
                agent_name="supervisor",
                task_id=task_id,
                task_type="direct",
            )

            # Get supervisor agent config from settings
            supervisor_config = settings.agents.definitions[0] if settings.agents.definitions else None

            if supervisor_config:
                agent_model = supervisor_config.model
                agent_provider = supervisor_config.provider
                agent_temp = supervisor_config.temperature or settings.agents.defaults.temperature
            else:
                # Fallback to defaults
                agent_model = "gpt-4o"
                agent_provider = "openai"
                agent_temp = 0.7

            # Record task assignment
            metrics_store.record_task_assignment(
                task_id=task_id,
                task_description=task,
                agent_name="supervisor",
                agent_config={
                    "model": agent_model,
                    "provider": agent_provider,
                    "temperature": agent_temp,
                },
            )

            # Update status
            metrics_store.update_task_status(task_id, "in_progress")

            console.print(f"[cyan]Task ID:[/cyan] {task_id}")
            console.print(f"[cyan]Agent:[/cyan] supervisor ({agent_provider}/{agent_model})")
            console.print(f"[cyan]Trace ID:[/cyan] {span.get_span_context().trace_id}")
            console.print()

            if dry_run:
                console.print("[yellow]Dry-run complete - no execution performed.[/yellow]\n")
                metrics_store.update_task_status(task_id, "completed", result_summary="Dry-run only")
                return

            # Create supervisor agent with LLM config
            console.print("[yellow]Initializing supervisor agent...[/yellow]")

            # Create FrameworkConfig (SupervisorAgent expects this, not LLMConfig)
            from ..legacy_config import FrameworkConfig
            from ..secrets import SecretManager

            # Try to get API key from multiple sources
            # Vertex AI uses gcloud auth, not API keys
            api_key = None

            if agent_provider == "vertex_ai":
                # Vertex AI uses Application Default Credentials (gcloud auth)
                # No API key needed, but we need project/location env vars
                api_key = "vertex-uses-adc"  # Placeholder
                console.print("[dim]Using Vertex AI with Application Default Credentials[/dim]")

            else:
                api_key_name = f"{agent_provider.upper()}_API_KEY"

                # Try 1Password first, then env var
                if agent_provider == "openai":
                    api_key = SecretManager.get_openai_api_key()
                elif agent_provider == "anthropic":
                    api_key = SecretManager.get_anthropic_api_key()
                else:
                    api_key = os.environ.get(api_key_name)

                if not api_key:
                    console.print(f"\n[red]Error:[/red] No API key found")
                    console.print(f"Please set: export {api_key_name}=your-key-here")
                    console.print(f"Or configure 1Password: OP_{agent_provider.upper()}_ITEM=op://...\n")
                    metrics_store.update_task_status(task_id, "failed", error_message="Missing API key")
                    raise typer.Exit(3)

            llm_config = LLMConfig(
                provider=agent_provider,
                models=[agent_model],
                temperature=agent_temp,
                api_key=api_key,
            )

            framework_config = FrameworkConfig(llm=llm_config)
            supervisor = SupervisorAgent(config=framework_config)

            # Branch: Multi-agent or single-agent execution
            if use_multi_agent:
                from .multi_agent_execution import execute_multi_agent

                console.print("[cyan]Using multi-agent execution (v0.2.0)[/cyan]\n")

                execution_result = execute_multi_agent(
                    task_description=task,
                    settings=settings,
                    supervisor=supervisor,
                    max_parallel=max_parallel,
                    metrics_store=metrics_store,
                    cost_calc=cost_calc,
                    console=console,
                )

                duration = time.time() - start_time

                # Record overall execution metrics
                metrics_store.update_task_status(
                    task_id,
                    "completed",
                    result_summary=f"Multi-agent: {execution_result['tasks_completed']}/{execution_result['tasks_total']} tasks",
                    trace_id=str(span.get_span_context().trace_id),
                    llm_calls_count=execution_result.get('tasks_total', 0),
                )

                console.print(f"[green]✓[/green] Multi-agent execution completed in {duration:.1f}s\n")
                return

            console.print("[yellow]Executing task with supervisor (single-agent)...[/yellow]\n")

            # Create callback to capture token usage
            token_callback = TokenUsageCallback()

            # Execute task and capture metrics
            with tracer.start_as_current_span("supervisor_decompose") as llm_span:
                # Execute task with callback
                result = supervisor.decompose_task(task, callbacks=[token_callback])

                # Get REAL token usage from callback
                usage = token_callback.get_usage()
                llm_calls_count = usage["call_count"]
                prompt_tokens = usage["prompt_tokens"]
                completion_tokens = usage["completion_tokens"]
                total_tokens = usage["total_tokens"]

                # If no tokens captured, fall back to estimation
                if total_tokens == 0:
                    console.print(f"[dim]No token usage captured, estimating...[/dim]")
                    prompt_tokens = len(task) // 4
                    completion_tokens = len(str(result)) // 4
                    total_tokens = prompt_tokens + completion_tokens

                # Calculate cost
                total_cost = cost_calc.calculate(
                    model=agent_model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    provider=agent_provider
                )

                # Set OTEL attributes
                llm_span.set_attribute("llm.model", agent_model)
                llm_span.set_attribute("llm.provider", agent_provider)
                llm_span.set_attribute("llm.usage.prompt_tokens", prompt_tokens)
                llm_span.set_attribute("llm.usage.completion_tokens", completion_tokens)
                llm_span.set_attribute("llm.usage.total_tokens", total_tokens)
                llm_span.set_attribute("llm.usage.cost_usd", total_cost)
                llm_span.set_attribute("llm.calls_count", llm_calls_count)

                is_estimated = usage["total_tokens"] == 0
                token_label = "estimated" if is_estimated else "actual"
                console.print(f"[dim]Tokens: {total_tokens:,} ({token_label})[/dim]")
                console.print(f"[dim]Cost: ${total_cost:.4f}[/dim]\n")

            duration = time.time() - start_time

            # Apply sub-phases if workflow phases configured
            subphase_results = []
            if settings.workflow.phases:
                console.print("[cyan]Applying sub-phases...[/cyan]")

                phase_executor = PhaseExecutor(
                    phases=settings.workflow.phases,
                    complexity=complexity if 'complexity' in locals() else "medium"
                )

                current_phase = phase_executor.get_current_phase()
                if current_phase:
                    console.print(f"[dim]Current phase: {current_phase.name}[/dim]")

                    subphase_results = phase_executor.apply_subphases_to_task(
                        task_id=task_id, task_result=result
                    )

                    # Display sub-phase results
                    for sp_result in subphase_results:
                        sp_name = sp_result.get("sub_phase")
                        sp_type = sp_result.get("type")
                        passed = sp_result.get("passed", False)

                        status = "✓" if passed else "✗"
                        console.print(f"  {status} {sp_name} ({sp_type})")

                        if not passed and "missing_files" in sp_result:
                            for missing in sp_result["missing_files"]:
                                console.print(f"    [red]Missing:[/red] {missing}")

                    console.print()

            # Extract results
            console.print("[green]✓ Task decomposed successfully![/green]\n")
            console.print(f"[cyan]Result:[/cyan]\n{result}\n")

            if subphase_results:
                console.print(f"[cyan]Sub-phases executed:[/cyan] {len(subphase_results)}\n")

            # Mark as completed with full metrics
            metrics_store.update_task_status(
                task_id,
                "completed",
                result_summary=str(result)[:500],
                trace_id=str(span.get_span_context().trace_id),
                llm_calls_count=llm_calls_count,
                total_tokens=total_tokens,
                total_cost_usd=total_cost,
            )

            # Record agent performance with cost
            metrics_store.record_agent_performance(
                agent_name="supervisor",
                task_id=task_id,
                success=True,
                duration_seconds=int(duration),
                cost_usd=total_cost,
            )

        console.print(f"[green]✓[/green] Task completed in {duration:.1f}s")
        console.print(f"[dim]Metrics saved to {metrics_store.db_path}[/dim]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]\n")
        metrics_store.update_task_status(task_id, "failed", error_message="Interrupted by user")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}\n")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        metrics_store.update_task_status(task_id, "failed", error_message=str(e))
        raise typer.Exit(1)


@app.command()
def init():
    """Initialize Tessera configuration with interactive wizard."""
    console.print(
        Panel.fit(
            "[bold cyan]Tessera Configuration Wizard[/bold cyan]\n"
            "[dim]Setting up ~/.config/tessera/config.yaml[/dim]",
            border_style="cyan",
        )
    )

    config_file = get_config_file_path()

    # Check if config already exists
    if config_file.exists():
        overwrite = Confirm.ask(
            f"\n[yellow]Config file already exists at {config_file}[/yellow]\n"
            "Overwrite it?",
            default=False
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
        default="openai"
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
    model = Prompt.ask(
        "Default model to use",
        default=default_models.get(provider, "gpt-4o")
    )

    # 4. Daily cost limit
    daily_limit = Prompt.ask(
        "Daily cost limit in USD (soft limit, just warnings)",
        default="10.00"
    )

    # Ensure directories exist
    dirs = ensure_directories()

    # Create minimal config from template
    import shutil
    from pathlib import Path

    template_path = Path(__file__).parent.parent / "config" / "defaults.yaml"

    # Copy template
    shutil.copy(template_path, config_file)

    # Update with user choices (simple replacement for v0.1)
    with open(config_file, 'r') as f:
        config_content = f.read()

    config_content = config_content.replace('provider: "openai"', f'provider: "{provider}"')
    config_content = config_content.replace('model: "gpt-4"', f'model: "{model}"')
    config_content = config_content.replace('daily_usd: 10.00', f'daily_usd: {daily_limit}')

    with open(config_file, 'w') as f:
        f.write(config_content)

    # Create default supervisor prompt
    supervisor_prompt_file = dirs['config_prompts'] / 'supervisor.md'
    if not supervisor_prompt_file.exists():
        from ..legacy_config import SUPERVISOR_PROMPT
        supervisor_prompt_file.write_text(SUPERVISOR_PROMPT)

    console.print(f"\n[green]✓[/green] Configuration created successfully!")
    console.print(f"\n[cyan]Config file:[/cyan] {config_file}")
    console.print(f"[cyan]Prompts directory:[/cyan] {dirs['config_prompts']}")
    console.print(f"[cyan]Cache directory:[/cyan] {dirs['cache']}\n")

    console.print("[yellow]Next steps:[/yellow]")
    console.print(f"  1. Review config: [dim]{config_file}[/dim]")
    console.print(f"  2. Set API key: [dim]export {api_key_env or 'YOUR_PROVIDER'}_API_KEY=...[/dim]")
    console.print(f"  3. Run Tessera: [dim]tessera[/dim]\n")

    # Test config load
    try:
        settings = TesseraSettings()
        console.print("[green]✓[/green] Configuration validated successfully!\n")
    except Exception as e:
        console.print(f"[red]Warning:[/red] Config validation failed: {e}\n")


@app.command()
def version():
    """Show Tessera version information."""
    console.print("[cyan]Tessera v0.1.0[/cyan]")
    console.print("[dim]Multi-Agent Orchestration Framework[/dim]\n")


if __name__ == "__main__":
    app()
