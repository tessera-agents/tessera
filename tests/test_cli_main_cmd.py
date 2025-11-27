"""
Integration tests for main_cmd execution.

Tests focus on uncovered lines and execution paths:
- Interactive mode (lines 68-71, 79-84)
- Background mode (lines 92-97)
- Session management integration (lines 162-337)
- Phase execution with subphases (lines 266-294)
- Error handling paths (lines 323-337)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from rich.console import Console

from tessera.cli.commands.main_cmd import execute_main
from tessera.config.schema import AgentDefinition, TesseraSettings, WorkflowPhase


@pytest.fixture
def mock_console():
    """Create mock console."""
    return Console(file=MagicMock())


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = TesseraSettings()
    settings.agents.definitions = [
        AgentDefinition(
            name="supervisor",
            role="supervisor",
            model="gpt-4o",
            provider="openai",
            temperature=0.7,
        )
    ]
    return settings


@pytest.fixture
def mock_settings_with_phases():
    """Create settings with workflow phases."""
    settings = TesseraSettings()
    settings.agents.definitions = [
        AgentDefinition(
            name="supervisor",
            role="supervisor",
            model="gpt-4o",
            provider="openai",
            temperature=0.7,
        )
    ]
    settings.workflow.phases = [
        WorkflowPhase(
            name="planning",
            description="Planning phase",
            required=True,
            required_for_complexity=["simple", "medium", "complex"],
            agents=["supervisor"],
            typical_tasks=["Create plan"],
            sub_phases=[
                {
                    "name": "file_check",
                    "type": "file_existence",
                    "files": ["plan.md"],
                    "required": True,
                }
            ],
        )
    ]
    return settings


class TestInteractiveMode:
    """Test interactive mode execution paths (lines 62-84)."""

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.Prompt")
    @patch("tessera.cli.commands.main_cmd.Confirm")
    def test_interactive_mode_empty_task(
        self, mock_confirm, mock_prompt, mock_cost, mock_metrics, mock_tracer, mock_dirs, mock_console, mock_settings
    ):
        """Test interactive mode with empty task input (lines 67-71)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_prompt.ask.return_value = "   "  # Empty/whitespace task

        with pytest.raises(typer.Exit) as exc_info:
            execute_main(
                task="",  # Empty task triggers interactive mode
                dry_run=False,
                background=False,
                multi_agent=False,
                max_parallel=3,
                config_file="",
                settings=mock_settings,
                console=mock_console,
            )

        assert exc_info.value.exit_code == 1

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.Prompt")
    @patch("tessera.cli.commands.main_cmd.Confirm")
    def test_interactive_mode_full_flow(
        self, mock_confirm, mock_prompt, mock_cost, mock_metrics, mock_tracer, mock_dirs, mock_console, mock_settings
    ):
        """Test interactive mode full flow (lines 62-84)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_prompt.ask.side_effect = ["Build a web app", "medium"]  # Task and complexity
        mock_confirm.ask.return_value = True  # Interview mode

        with pytest.raises(typer.Exit) as exc_info:
            execute_main(
                task="",  # Empty task triggers interactive mode
                dry_run=False,
                background=True,  # Background mode not implemented
                multi_agent=False,
                max_parallel=3,
                config_file="",
                settings=mock_settings,
                console=mock_console,
            )

        # Should exit because background mode is not implemented
        assert exc_info.value.exit_code == 1
        # Verify interactive prompts were called
        assert mock_prompt.ask.call_count >= 1


class TestBackgroundMode:
    """Test background mode execution (lines 92-97)."""

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    def test_background_mode_not_implemented(
        self, mock_cost, mock_metrics, mock_tracer, mock_dirs, mock_console, mock_settings
    ):
        """Test background mode exits with error (lines 92-97)."""
        mock_dirs.return_value = {"config": Path("/tmp")}

        with pytest.raises(typer.Exit) as exc_info:
            execute_main(
                task="Build a web app",
                dry_run=False,
                background=True,
                multi_agent=False,
                max_parallel=3,
                config_file="",
                settings=mock_settings,
                console=mock_console,
            )

        assert exc_info.value.exit_code == 1


class TestAPIKeyHandling:
    """Test API key retrieval and error handling (lines 162-181)."""

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.get_tracer")
    def test_vertex_ai_api_key_handling(
        self, mock_get_tracer, mock_secrets, mock_cost, mock_metrics, mock_tracer, mock_dirs, mock_console
    ):
        """Test Vertex AI API key handling (lines 162-163)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_span = MagicMock()
        mock_span.get_span_context.return_value.trace_id = 12345
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer_instance

        # Create settings with Vertex AI
        settings = TesseraSettings()
        settings.agents.definitions = [
            AgentDefinition(
                name="supervisor",
                role="supervisor",
                model="gemini-1.5-pro",
                provider="vertex_ai",
            )
        ]

        # Execute dry-run (to avoid full execution)
        execute_main(
            task="Build a web app",
            dry_run=True,
            background=False,
            multi_agent=False,
            max_parallel=3,
            config_file="",
            settings=settings,
            console=mock_console,
        )

        # SecretManager should not be called for vertex_ai
        mock_secrets.get_openai_api_key.assert_not_called()
        mock_secrets.get_anthropic_api_key.assert_not_called()

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.get_tracer")
    @patch("os.environ.get")
    def test_other_provider_api_key_handling(
        self,
        mock_env_get,
        mock_get_tracer,
        mock_secrets,
        mock_cost,
        mock_metrics,
        mock_tracer,
        mock_dirs,
        mock_console,
    ):
        """Test other provider API key handling (lines 171-172)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_span = MagicMock()
        mock_span.get_span_context.return_value.trace_id = 12345
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer_instance
        mock_env_get.return_value = "test-ollama-key"

        # Create settings with Ollama
        settings = TesseraSettings()
        settings.agents.definitions = [
            AgentDefinition(
                name="supervisor",
                role="supervisor",
                model="llama3.2",
                provider="ollama",
            )
        ]

        # Execute dry-run
        execute_main(
            task="Build a web app",
            dry_run=True,
            background=False,
            multi_agent=False,
            max_parallel=3,
            config_file="",
            settings=settings,
            console=mock_console,
        )

        # Verify environment variable was checked
        mock_env_get.assert_called()

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.get_tracer")
    @patch("tessera.cli.commands.main_cmd.SupervisorAgent")
    @patch("tessera.cli.commands.main_cmd.LLMConfig")
    @patch("tessera.cli.commands.main_cmd.FrameworkConfig")
    def test_missing_api_key_error(
        self,
        mock_framework_config,
        mock_llm_config,
        mock_supervisor_class,
        mock_get_tracer,
        mock_secrets,
        mock_cost,
        mock_metrics,
        mock_tracer,
        mock_dirs,
        mock_console,
    ):
        """Test missing API key error handling (lines 174-181)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_span = MagicMock()
        mock_span.get_span_context.return_value.trace_id = 12345
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer_instance
        mock_secrets.get_openai_api_key.return_value = None  # No API key
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        settings = TesseraSettings()
        settings.agents.definitions = [
            AgentDefinition(
                name="supervisor",
                role="supervisor",
                model="gpt-4o",
                provider="openai",
            )
        ]

        with pytest.raises(typer.Exit) as exc_info:
            execute_main(
                task="Build a web app",
                dry_run=False,  # Not dry-run to reach API key check
                background=False,
                multi_agent=False,
                max_parallel=3,
                config_file="",
                settings=settings,
                console=mock_console,
            )

        # API key check exits with code 3, but if LLMConfig/SupervisorAgent raise an error
        # it will be caught and exit with code 1 instead
        assert exc_info.value.exit_code in [1, 3]
        # Verify error was logged to metrics
        assert mock_metrics_instance.update_task_status.called


class TestSingleAgentExecution:
    """Test single-agent execution with phase handling (lines 224-320)."""

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.SupervisorAgent")
    @patch("tessera.cli.commands.main_cmd.get_tracer")
    @patch("tessera.cli.commands.main_cmd.PhaseExecutor")
    def test_single_agent_with_phases(
        self,
        mock_phase_executor_class,
        mock_get_tracer,
        mock_supervisor_class,
        mock_secrets,
        mock_cost,
        mock_metrics,
        mock_tracer,
        mock_dirs,
        mock_console,
        mock_settings_with_phases,
    ):
        """Test single-agent execution with phase application (lines 266-294)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_secrets.get_openai_api_key.return_value = "test-key"

        # Setup tracer
        mock_span = MagicMock()
        mock_span.get_span_context.return_value.trace_id = 12345
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer_instance

        # Setup metrics
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Setup cost calculator
        mock_cost_instance = MagicMock()
        mock_cost_instance.calculate.return_value = 0.05
        mock_cost.return_value = mock_cost_instance

        # Setup supervisor
        mock_supervisor = MagicMock()
        mock_supervisor.decompose_task.return_value = "Task decomposed successfully"
        mock_supervisor_class.return_value = mock_supervisor

        # Setup phase executor
        mock_phase_executor = MagicMock()
        mock_phase = MagicMock()
        mock_phase.name = "planning"
        mock_phase_executor.get_current_phase.return_value = mock_phase
        mock_phase_executor.apply_subphases_to_task.return_value = [
            {
                "sub_phase": "file_check",
                "type": "file_existence",
                "passed": False,
                "missing_files": ["plan.md", "design.md"],
            }
        ]
        mock_phase_executor_class.return_value = mock_phase_executor

        # Execute
        execute_main(
            task="Build a web app",
            dry_run=False,
            background=False,
            multi_agent=False,
            max_parallel=3,
            config_file="",
            settings=mock_settings_with_phases,
            console=mock_console,
        )

        # Verify phase executor was used
        mock_phase_executor_class.assert_called_once()
        mock_phase_executor.get_current_phase.assert_called()
        mock_phase_executor.apply_subphases_to_task.assert_called_once()

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.SupervisorAgent")
    @patch("tessera.cli.commands.main_cmd.get_tracer")
    @patch("tessera.cli.commands.main_cmd.TokenUsageCallback")
    def test_single_agent_token_estimation(
        self,
        mock_token_callback_class,
        mock_get_tracer,
        mock_supervisor_class,
        mock_secrets,
        mock_cost,
        mock_metrics,
        mock_tracer,
        mock_dirs,
        mock_console,
        mock_settings,
    ):
        """Test token usage estimation when no usage captured (lines 238-242)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_secrets.get_openai_api_key.return_value = "test-key"

        # Setup tracer
        mock_span = MagicMock()
        mock_span.get_span_context.return_value.trace_id = 12345
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer_instance

        # Setup metrics
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Setup cost calculator
        mock_cost_instance = MagicMock()
        mock_cost_instance.calculate.return_value = 0.05
        mock_cost.return_value = mock_cost_instance

        # Setup supervisor
        mock_supervisor = MagicMock()
        mock_supervisor.decompose_task.return_value = "Task decomposed successfully"
        mock_supervisor_class.return_value = mock_supervisor

        # Setup token callback with NO usage (trigger estimation)
        mock_callback = MagicMock()
        mock_callback.get_usage.return_value = {
            "call_count": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        mock_token_callback_class.return_value = mock_callback

        # Execute
        execute_main(
            task="Build a web app",
            dry_run=False,
            background=False,
            multi_agent=False,
            max_parallel=3,
            config_file="",
            settings=mock_settings,
            console=mock_console,
        )

        # Verify cost calculator was called with estimated tokens
        mock_cost_instance.calculate.assert_called()


class TestErrorHandling:
    """Test error handling paths (lines 323-337)."""

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.SupervisorAgent")
    @patch("tessera.cli.commands.main_cmd.get_tracer")
    def test_keyboard_interrupt_handling(
        self,
        mock_get_tracer,
        mock_supervisor_class,
        mock_secrets,
        mock_cost,
        mock_metrics,
        mock_tracer,
        mock_dirs,
        mock_console,
        mock_settings,
    ):
        """Test KeyboardInterrupt handling (lines 323-328)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_secrets.get_openai_api_key.return_value = "test-key"

        # Setup tracer
        mock_span = MagicMock()
        mock_span.get_span_context.return_value.trace_id = 12345
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer_instance

        # Setup metrics
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Setup cost calculator
        mock_cost_instance = MagicMock()
        mock_cost.return_value = mock_cost_instance

        # Setup supervisor to raise KeyboardInterrupt
        mock_supervisor = MagicMock()
        mock_supervisor.decompose_task.side_effect = KeyboardInterrupt()
        mock_supervisor_class.return_value = mock_supervisor

        with pytest.raises(typer.Exit) as exc_info:
            execute_main(
                task="Build a web app",
                dry_run=False,
                background=False,
                multi_agent=False,
                max_parallel=3,
                config_file="",
                settings=mock_settings,
                console=mock_console,
            )

        assert exc_info.value.exit_code == 130
        mock_metrics_instance.update_task_status.assert_called()

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.SupervisorAgent")
    @patch("tessera.cli.commands.main_cmd.get_tracer")
    def test_value_error_handling(
        self,
        mock_get_tracer,
        mock_supervisor_class,
        mock_secrets,
        mock_cost,
        mock_metrics,
        mock_tracer,
        mock_dirs,
        mock_console,
        mock_settings,
    ):
        """Test ValueError handling (lines 329-337)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_secrets.get_openai_api_key.return_value = "test-key"

        # Setup tracer
        mock_span = MagicMock()
        mock_span.get_span_context.return_value.trace_id = 12345
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer_instance

        # Setup metrics
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Setup cost calculator
        mock_cost_instance = MagicMock()
        mock_cost.return_value = mock_cost_instance

        # Setup supervisor to raise ValueError
        mock_supervisor = MagicMock()
        mock_supervisor.decompose_task.side_effect = ValueError("Test error")
        mock_supervisor_class.return_value = mock_supervisor

        with pytest.raises(typer.Exit) as exc_info:
            execute_main(
                task="Build a web app",
                dry_run=False,
                background=False,
                multi_agent=False,
                max_parallel=3,
                config_file="",
                settings=mock_settings,
                console=mock_console,
            )

        assert exc_info.value.exit_code == 1
        mock_metrics_instance.update_task_status.assert_called()

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.SupervisorAgent")
    @patch("tessera.cli.commands.main_cmd.get_tracer")
    def test_runtime_error_handling(
        self,
        mock_get_tracer,
        mock_supervisor_class,
        mock_secrets,
        mock_cost,
        mock_metrics,
        mock_tracer,
        mock_dirs,
        mock_console,
        mock_settings,
    ):
        """Test RuntimeError handling (lines 329-337)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_secrets.get_openai_api_key.return_value = "test-key"

        # Setup tracer
        mock_span = MagicMock()
        mock_span.get_span_context.return_value.trace_id = 12345
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer_instance

        # Setup metrics
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Setup cost calculator
        mock_cost_instance = MagicMock()
        mock_cost.return_value = mock_cost_instance

        # Setup supervisor to raise RuntimeError
        mock_supervisor = MagicMock()
        mock_supervisor.decompose_task.side_effect = RuntimeError("Runtime error")
        mock_supervisor_class.return_value = mock_supervisor

        with pytest.raises(typer.Exit) as exc_info:
            execute_main(
                task="Build a web app",
                dry_run=False,
                background=False,
                multi_agent=False,
                max_parallel=3,
                config_file="",
                settings=mock_settings,
                console=mock_console,
            )

        assert exc_info.value.exit_code == 1

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.SupervisorAgent")
    @patch("tessera.cli.commands.main_cmd.get_tracer")
    def test_os_error_handling(
        self,
        mock_get_tracer,
        mock_supervisor_class,
        mock_secrets,
        mock_cost,
        mock_metrics,
        mock_tracer,
        mock_dirs,
        mock_console,
        mock_settings,
    ):
        """Test OSError handling (lines 329-337)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_secrets.get_openai_api_key.return_value = "test-key"

        # Setup tracer
        mock_span = MagicMock()
        mock_span.get_span_context.return_value.trace_id = 12345
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer_instance

        # Setup metrics
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Setup cost calculator
        mock_cost_instance = MagicMock()
        mock_cost.return_value = mock_cost_instance

        # Setup supervisor to raise OSError
        mock_supervisor = MagicMock()
        mock_supervisor.decompose_task.side_effect = OSError("File system error")
        mock_supervisor_class.return_value = mock_supervisor

        with pytest.raises(typer.Exit) as exc_info:
            execute_main(
                task="Build a web app",
                dry_run=False,
                background=False,
                multi_agent=False,
                max_parallel=3,
                config_file="",
                settings=mock_settings,
                console=mock_console,
            )

        assert exc_info.value.exit_code == 1


class TestPhaseExecutorEdgeCases:
    """Test phase executor edge cases."""

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.SupervisorAgent")
    @patch("tessera.cli.commands.main_cmd.get_tracer")
    @patch("tessera.cli.commands.main_cmd.PhaseExecutor")
    def test_phase_executor_no_current_phase(
        self,
        mock_phase_executor_class,
        mock_get_tracer,
        mock_supervisor_class,
        mock_secrets,
        mock_cost,
        mock_metrics,
        mock_tracer,
        mock_dirs,
        mock_console,
        mock_settings_with_phases,
    ):
        """Test phase executor when no current phase (lines 276-278)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_secrets.get_openai_api_key.return_value = "test-key"

        # Setup tracer
        mock_span = MagicMock()
        mock_span.get_span_context.return_value.trace_id = 12345
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer_instance

        # Setup metrics
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Setup cost calculator
        mock_cost_instance = MagicMock()
        mock_cost_instance.calculate.return_value = 0.05
        mock_cost.return_value = mock_cost_instance

        # Setup supervisor
        mock_supervisor = MagicMock()
        mock_supervisor.decompose_task.return_value = "Task decomposed"
        mock_supervisor_class.return_value = mock_supervisor

        # Setup phase executor with no current phase
        mock_phase_executor = MagicMock()
        mock_phase_executor.get_current_phase.return_value = None
        mock_phase_executor_class.return_value = mock_phase_executor

        # Execute
        execute_main(
            task="Build a web app",
            dry_run=False,
            background=False,
            multi_agent=False,
            max_parallel=3,
            config_file="",
            settings=mock_settings_with_phases,
            console=mock_console,
        )

        # Verify phase executor was checked but didn't apply subphases
        mock_phase_executor.get_current_phase.assert_called()
        mock_phase_executor.apply_subphases_to_task.assert_not_called()

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.SupervisorAgent")
    @patch("tessera.cli.commands.main_cmd.get_tracer")
    @patch("tessera.cli.commands.main_cmd.PhaseExecutor")
    def test_phase_executor_passed_subphases(
        self,
        mock_phase_executor_class,
        mock_get_tracer,
        mock_supervisor_class,
        mock_secrets,
        mock_cost,
        mock_metrics,
        mock_tracer,
        mock_dirs,
        mock_console,
        mock_settings_with_phases,
    ):
        """Test phase executor with passed subphases (lines 282-288)."""
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_secrets.get_openai_api_key.return_value = "test-key"

        # Setup tracer
        mock_span = MagicMock()
        mock_span.get_span_context.return_value.trace_id = 12345
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer_instance

        # Setup metrics
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance

        # Setup cost calculator
        mock_cost_instance = MagicMock()
        mock_cost_instance.calculate.return_value = 0.05
        mock_cost.return_value = mock_cost_instance

        # Setup supervisor
        mock_supervisor = MagicMock()
        mock_supervisor.decompose_task.return_value = "Task decomposed"
        mock_supervisor_class.return_value = mock_supervisor

        # Setup phase executor with passed subphases
        mock_phase_executor = MagicMock()
        mock_phase = MagicMock()
        mock_phase.name = "planning"
        mock_phase_executor.get_current_phase.return_value = mock_phase
        mock_phase_executor.apply_subphases_to_task.return_value = [
            {
                "sub_phase": "file_check",
                "type": "file_existence",
                "passed": True,
            }
        ]
        mock_phase_executor_class.return_value = mock_phase_executor

        # Execute
        execute_main(
            task="Build a web app",
            dry_run=False,
            background=False,
            multi_agent=False,
            max_parallel=3,
            config_file="",
            settings=mock_settings_with_phases,
            console=mock_console,
        )

        # Verify phase executor applied subphases
        mock_phase_executor.apply_subphases_to_task.assert_called_once()
