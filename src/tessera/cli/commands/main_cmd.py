"""Main task execution command implementation."""

import os
import time
import uuid

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from tessera.config.schema import TesseraSettings
from tessera.config.xdg import ensure_directories
from tessera.legacy_config import FrameworkConfig, LLMConfig
from tessera.observability import CostCalculator, MetricsStore, TokenUsageCallback, init_tracer
from tessera.observability.tracer import get_tracer, set_span_attributes
from tessera.secrets import SecretManager
from tessera.supervisor import SupervisorAgent
from tessera.workflow import PhaseExecutor


def execute_main(
    task: str,
    dry_run: bool,
    background: bool,
    multi_agent: bool,
    max_parallel: int,
    config_file: str,
    settings: TesseraSettings,
    console: Console,
) -> None:
    """
    Execute main task command.

    Args:
        task: Task description
        dry_run: Dry-run mode (plan only)
        background: Background execution
        multi_agent: Force multi-agent mode
        max_parallel: Max parallel agents
        config_file: Custom config file path
        settings: Loaded settings
        console: Rich console instance
    """
    console.print(
        Panel.fit(
            "[bold cyan]TESSERA[/bold cyan]\nMulti-Agent Orchestration Framework\n[dim]v0.3.0 - Production Ready[/dim]",
            border_style="cyan",
        )
    )

    # Ensure directories exist
    dirs = ensure_directories()
    console.print(f"[dim]Config: {dirs['config']}[/dim]\n")

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
            import typer

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
        import typer

        raise typer.Exit(1)

    # Check if multi-agent mode should be used
    use_multi_agent = multi_agent or len(settings.agents.definitions) > 1

    if use_multi_agent and len(settings.agents.definitions) > 1:
        console.print(f"[cyan]Multi-agent mode:[/cyan] {len(settings.agents.definitions)} agents\n")
    else:
        use_multi_agent = False

    # Execute task
    try:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        tracer = get_tracer()
        start_time = time.time()

        with tracer.start_as_current_span("tessera_task_execution") as span:
            set_span_attributes(agent_name="supervisor", task_id=task_id, task_type="direct")

            # Get supervisor config
            supervisor_config = settings.agents.definitions[0] if settings.agents.definitions else None

            if supervisor_config:
                agent_model = supervisor_config.model
                agent_provider = supervisor_config.provider
                agent_temp = supervisor_config.temperature or settings.agents.defaults.temperature
            else:
                agent_model = "gpt-4o"
                agent_provider = "openai"
                agent_temp = 0.7

            # Record task
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

            metrics_store.update_task_status(task_id, "in_progress")

            console.print(f"[cyan]Task ID:[/cyan] {task_id}")
            console.print(f"[cyan]Agent:[/cyan] supervisor ({agent_provider}/{agent_model})")
            console.print(f"[cyan]Trace ID:[/cyan] {span.get_span_context().trace_id}")
            console.print()

            if dry_run:
                console.print("[yellow]Dry-run complete - no execution performed.[/yellow]\n")
                metrics_store.update_task_status(task_id, "completed", result_summary="Dry-run only")
                return

            # Create supervisor agent
            console.print("[yellow]Initializing supervisor agent...[/yellow]")

            # Get API key
            api_key = None

            if agent_provider == "vertex_ai":
                api_key = "vertex-uses-adc"
                console.print("[dim]Using Vertex AI with Application Default Credentials[/dim]")
            else:
                api_key_name = f"{agent_provider.upper()}_API_KEY"

                if agent_provider == "openai":
                    api_key = SecretManager.get_openai_api_key()
                elif agent_provider == "anthropic":
                    api_key = SecretManager.get_anthropic_api_key()
                else:
                    api_key = os.environ.get(api_key_name)

                if not api_key:
                    console.print("\n[red]Error:[/red] No API key found")
                    console.print(f"Please set: export {api_key_name}=your-key-here")
                    console.print(f"Or configure 1Password: OP_{agent_provider.upper()}_ITEM=op://...\n")
                    metrics_store.update_task_status(task_id, "failed", error_message="Missing API key")
                    import typer

                    raise typer.Exit(3)

            llm_config = LLMConfig(
                provider=agent_provider,
                models=[agent_model],
                temperature=agent_temp,
                api_key=api_key,
            )

            framework_config = FrameworkConfig(llm=llm_config)
            supervisor = SupervisorAgent(config=framework_config)

            # Multi-agent or single-agent
            if use_multi_agent:
                from tessera.cli.multi_agent_execution import execute_multi_agent

                console.print("[cyan]Using multi-agent execution (v0.3.0)[/cyan]\n")

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

                metrics_store.update_task_status(
                    task_id,
                    "completed",
                    result_summary=(
                        f"Multi-agent: {execution_result['tasks_completed']}/{execution_result['tasks_total']} tasks"
                    ),
                    trace_id=str(span.get_span_context().trace_id),
                    llm_calls_count=execution_result.get("tasks_total", 0),
                )

                console.print(f"[green]✓[/green] Multi-agent execution completed in {duration:.1f}s\n")
                return

            console.print("[yellow]Executing task with supervisor (single-agent)...[/yellow]\n")

            # Single-agent execution
            token_callback = TokenUsageCallback()

            with tracer.start_as_current_span("supervisor_decompose") as llm_span:
                result = supervisor.decompose_task(task, callbacks=[token_callback])

                usage = token_callback.get_usage()
                llm_calls_count = usage["call_count"]
                prompt_tokens = usage["prompt_tokens"]
                completion_tokens = usage["completion_tokens"]
                total_tokens = usage["total_tokens"]

                if total_tokens == 0:
                    console.print("[dim]No token usage captured, estimating...[/dim]")
                    prompt_tokens = len(task) // 4
                    completion_tokens = len(str(result)) // 4
                    total_tokens = prompt_tokens + completion_tokens

                total_cost = cost_calc.calculate(
                    model=agent_model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    provider=agent_provider,
                )

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

            # Apply sub-phases if configured
            subphase_results = []
            if settings.workflow.phases:
                console.print("[cyan]Applying sub-phases...[/cyan]")

                phase_executor = PhaseExecutor(
                    phases=settings.workflow.phases,
                    complexity=complexity if "complexity" in locals() else "medium",
                )

                current_phase = phase_executor.get_current_phase()
                if current_phase:
                    console.print(f"[dim]Current phase: {current_phase.name}[/dim]")

                    subphase_results = phase_executor.apply_subphases_to_task(task_id=task_id, task_result=result)

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

            console.print("[green]✓ Task decomposed successfully![/green]\n")
            console.print(f"[cyan]Result:[/cyan]\n{result}\n")

            if subphase_results:
                console.print(f"[cyan]Sub-phases executed:[/cyan] {len(subphase_results)}\n")

            metrics_store.update_task_status(
                task_id,
                "completed",
                result_summary=str(result)[:500],
                trace_id=str(span.get_span_context().trace_id),
                llm_calls_count=llm_calls_count,
                total_tokens=total_tokens,
                total_cost_usd=total_cost,
            )

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
        metrics_store.update_task_status(task_id, "failed", error_message="Interrupted by user")  # type: ignore[possibly-undefined]
        import typer

        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}\n")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        metrics_store.update_task_status(task_id, "failed", error_message=str(e))  # type: ignore[possibly-undefined]
        import typer

        raise typer.Exit(1)
