#!/usr/bin/env python3
"""
Example demonstrating rate limiting and retry configuration.

This example shows:
1. Starting copilot-api proxy with subprocess (no Docker needed)
2. Configuring client-side retries
3. Testing rate limit behavior
4. Handling errors gracefully
"""

import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from autonomy import SupervisorAgent, start_proxy, stop_proxy, is_proxy_running
from tessera.config import LLMConfig
from tessera.copilot_proxy import CopilotProxyManager

console = Console()


def example_1_basic_proxy_management():
    """Example 1: Start and stop proxy with subprocess."""

    console.print("\n[bold cyan]Example 1: Basic Proxy Management[/bold cyan]\n")

    # Start proxy with subprocess
    console.print("[yellow]Starting copilot-api proxy...[/yellow]")

    success = start_proxy(
        rate_limit=30,  # 30-second minimum between requests
        use_wait=True,  # Wait during cooldown instead of rejecting
        wait_for_ready=True,  # Block until server is ready
    )

    if success:
        console.print("[green]✓ Proxy started successfully[/green]")
        console.print(f"  Running: {is_proxy_running()}")
    else:
        console.print("[red]✗ Failed to start proxy[/red]")
        return

    # Use proxy
    console.print("\n[yellow]Making a request through proxy...[/yellow]")

    try:
        config = LLMConfig.from_env(provider="openai")
        supervisor = SupervisorAgent(config=config)

        task = supervisor.decompose_task("Create a simple hello world program")

        console.print("[green]✓ Request successful[/green]")
        console.print(f"  Goal: {task.goal}")
        console.print(f"  Subtasks: {len(task.subtasks)}")

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")

    # Stop proxy
    console.print("\n[yellow]Stopping proxy...[/yellow]")
    stop_proxy()
    console.print("[green]✓ Proxy stopped[/green]")


def example_2_context_manager():
    """Example 2: Using proxy as context manager."""

    console.print("\n[bold cyan]Example 2: Context Manager[/bold cyan]\n")

    console.print("[yellow]Using proxy with context manager (auto-cleanup)...[/yellow]")

    # Proxy automatically starts and stops
    with CopilotProxyManager(rate_limit=30, use_wait=True) as proxy:
        console.print(f"[green]✓ Proxy running at {proxy.get_base_url()}[/green]")

        # Create config pointing to proxy
        config = LLMConfig(
            provider="openai",
            base_url=proxy.get_base_url(),
            max_retries=3,  # Client-side retries
            timeout=90.0,  # Timeout for queued requests
        )

        supervisor = SupervisorAgent(config=config)
        task = supervisor.decompose_task("Build a REST API")

        console.print(f"[green]✓ Task created: {task.goal}[/green]")

    # Proxy automatically stopped here
    console.print("[green]✓ Proxy automatically stopped (context manager exit)[/green]")


def example_3_retry_configuration():
    """Example 3: Configure retry behavior."""

    console.print("\n[bold cyan]Example 3: Retry Configuration[/bold cyan]\n")

    # Show different retry configurations
    configs = [
        {
            "name": "Conservative (Default)",
            "max_retries": 3,
            "timeout": 60.0,
            "description": "3 retries, 60s timeout",
        },
        {
            "name": "Aggressive",
            "max_retries": 5,
            "timeout": 120.0,
            "description": "5 retries, 2min timeout",
        },
        {
            "name": "No Retries",
            "max_retries": 0,
            "timeout": 30.0,
            "description": "Fail fast, no retries",
        },
    ]

    table = Table(title="Retry Configurations")
    table.add_column("Configuration", style="cyan")
    table.add_column("Max Retries", style="yellow")
    table.add_column("Timeout", style="green")
    table.add_column("Description")

    for cfg in configs:
        table.add_row(
            cfg["name"],
            str(cfg["max_retries"]),
            f"{cfg['timeout']}s",
            cfg["description"],
        )

    console.print(table)

    # Demonstrate usage
    console.print("\n[yellow]Using aggressive retry configuration...[/yellow]")

    config = LLMConfig(
        provider="openai",
        max_retries=5,  # More retries
        timeout=120.0,  # Longer timeout
        model="gpt-4",
    )

    console.print(f"[green]✓ Configuration created with {config.max_retries} max retries[/green]")


def example_4_rate_limit_testing():
    """Example 4: Test rate limiting behavior."""

    console.print("\n[bold cyan]Example 4: Rate Limit Testing[/bold cyan]\n")

    console.print("[yellow]Starting proxy with 30-second rate limit...[/yellow]")

    with CopilotProxyManager(rate_limit=30, use_wait=True) as proxy:
        config = LLMConfig(
            provider="openai",
            base_url=proxy.get_base_url(),
            max_retries=3,
            timeout=90.0,
        )

        supervisor = SupervisorAgent(config=config)

        # Make rapid requests to test rate limiting
        console.print("\n[yellow]Making 3 rapid requests...[/yellow]")

        for i in range(3):
            console.print(f"\n[cyan]Request {i+1}:[/cyan]")

            start = time.time()

            try:
                task = supervisor.decompose_task(f"Test task {i+1}")
                elapsed = time.time() - start

                console.print(f"  [green]✓ Completed in {elapsed:.1f}s[/green]")
                console.print(f"  Subtasks: {len(task.subtasks)}")

                if i > 0 and elapsed > 25:
                    console.print("  [yellow]⏱ Rate limit queue wait detected![/yellow]")

            except Exception as e:
                elapsed = time.time() - start
                console.print(f"  [red]✗ Failed after {elapsed:.1f}s: {e}[/red]")

            # Small delay between attempts (not necessary with --wait, but cleaner logs)
            if i < 2:
                time.sleep(1)


def example_5_error_handling():
    """Example 5: Proper error handling."""

    console.print("\n[bold cyan]Example 5: Error Handling[/bold cyan]\n")

    from openai import RateLimitError, APITimeoutError
    import sys

    def robust_request(objective: str, max_attempts: int = 3) -> None:
        """Make request with additional application-level retry logic."""

        for attempt in range(max_attempts):
            try:
                config = LLMConfig.from_env(provider="openai")
                supervisor = SupervisorAgent(config=config)

                task = supervisor.decompose_task(objective)

                console.print(f"[green]✓ Success on attempt {attempt + 1}[/green]")
                console.print(f"  Goal: {task.goal}")
                return

            except RateLimitError as e:
                if attempt < max_attempts - 1:
                    wait_time = 60 * (attempt + 1)  # Progressive backoff
                    console.print(
                        f"[yellow]⚠ Rate limited, waiting {wait_time}s...[/yellow]"
                    )
                    time.sleep(wait_time)
                else:
                    console.print(f"[red]✗ Max retries reached: {e}[/red]")
                    raise

            except APITimeoutError as e:
                if attempt < max_attempts - 1:
                    console.print(
                        f"[yellow]⚠ Timeout on attempt {attempt + 1}, retrying...[/yellow]"
                    )
                    time.sleep(5)
                else:
                    console.print(f"[red]✗ Max retries reached: {e}[/red]")
                    raise

            except Exception as e:
                console.print(f"[red]✗ Unexpected error: {e}[/red]")
                raise

    console.print("[yellow]Making request with error handling...[/yellow]")

    try:
        robust_request("Build authentication system")
    except Exception as e:
        console.print(f"[red]Request failed after all retries: {e}[/red]")


def main():
    """Run all examples."""

    console.print(Panel.fit(
        "[bold cyan]Rate Limiting & Retry Configuration Examples[/bold cyan]\n\n"
        "This demonstrates:\n"
        "• Subprocess-based proxy management (no Docker)\n"
        "• Client-side retry configuration\n"
        "• Rate limit behavior testing\n"
        "• Error handling best practices",
        border_style="cyan"
    ))

    try:
        # Run examples
        example_1_basic_proxy_management()
        example_2_context_manager()
        example_3_retry_configuration()

        # These require running proxy
        console.print("\n[yellow]⚠ Examples 4-5 require active proxy[/yellow]")
        console.print("[yellow]  Run them individually if you have proxy running[/yellow]")

        # Uncomment to run (requires proxy):
        # example_4_rate_limit_testing()
        # example_5_error_handling()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback

        traceback.print_exc()
    finally:
        # Ensure proxy is stopped
        if is_proxy_running():
            console.print("\n[yellow]Cleaning up proxy...[/yellow]")
            stop_proxy()

    console.print("\n[bold green]Examples complete![/bold green]")


if __name__ == "__main__":
    main()
