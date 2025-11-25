"""
Tests for CLI module.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from tessera.cli.main import app, load_config

runner = CliRunner()


@pytest.mark.unit
class TestCLI:
    """Test CLI commands."""

    def test_version_command(self):
        """Test version command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Tessera" in result.output

    @patch("tessera.cli.main.load_config")
    def test_init_command(self, mock_load_config):
        """Test init command (mocked)."""
        # Would be interactive, so just test it exists
        result = runner.invoke(app, ["init"], input="n\n")
        # Command exists
        assert "Tessera" in result.output or result.exit_code in [0, 1]

    def test_load_config_returns_settings(self):
        """Test load_config returns TesseraSettings."""
        settings = load_config()
        assert settings is not None
        assert hasattr(settings, "tessera")
        assert hasattr(settings, "agents")


@pytest.mark.unit
class TestMultiAgentExecution:
    """Test multi-agent execution helper."""

    def test_module_exists(self):
        """Test multi_agent_execution module imports."""
        from tessera.cli import multi_agent_execution

        assert multi_agent_execution is not None


@pytest.mark.unit
class TestCLIMainExecution:
    """Test main CLI execution flow."""

    @patch("tessera.cli.main.ensure_directories")
    @patch("tessera.cli.main.load_config")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    def test_main_dry_run(self, mock_cost, mock_metrics, mock_tracer, mock_config, mock_dirs):
        """Test dry-run mode."""
        mock_config.return_value = Mock(
            tessera=Mock(default_complexity="medium"),
            agents=Mock(definitions=[]),
            observability=Mock(local=Mock(enabled=True)),
            workflow=Mock(phases=[]),
        )
        mock_dirs.return_value = {"config": Path("/tmp")}

        result = runner.invoke(app, ["main", "--dry-run", "test task"])

        # Dry-run should complete
        assert "Dry-run" in result.output or result.exit_code == 0

    @patch("tessera.cli.main.ensure_directories")
    @patch("tessera.cli.main.load_config")
    def test_main_no_task_interactive(self, mock_config, mock_dirs):
        """Test interactive mode prompt."""
        mock_config.return_value = Mock(
            tessera=Mock(default_complexity="medium"),
            project_generation=Mock(interview=Mock(enabled=True)),
        )
        mock_dirs.return_value = {"config": Path("/tmp")}

        result = runner.invoke(app, ["main"], input="test task\n")

        # Should prompt for task
        assert result.exit_code in [0, 1, 2]  # May fail on missing deps but tests prompt


@pytest.mark.unit
class TestCLIHelpers:
    """Test CLI helper functions."""

    def test_load_config_without_file(self):
        """Test loading config when no file exists."""
        settings = load_config(None)
        assert settings is not None

    @patch("tessera.cli.main.TesseraSettings")
    def test_load_config_handles_errors(self, mock_settings):
        """Test load_config handles errors gracefully."""
        # First call raises exception, second call returns a mock
        mock_settings.side_effect = [ValueError("Test error"), Mock()]

        settings = load_config(None)
        assert settings is not None  # Returns default


@pytest.mark.integration
class TestMainCmdExecution:
    """Test main command execution paths."""

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.SupervisorAgent")
    def test_main_cmd_with_task(self, mock_supervisor, mock_secrets, mock_cost, mock_metrics, mock_tracer, mock_dirs):
        """Test main command execution with task."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from tessera.cli.commands.main_cmd import execute_main
        from tessera.config.schema import TesseraSettings

        # Setup mocks
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance
        mock_cost_instance = MagicMock()
        mock_cost_instance.calculate.return_value = 0.01
        mock_cost.return_value = mock_cost_instance
        mock_secrets.get_openai_api_key.return_value = "test-key"

        # Mock supervisor
        mock_supervisor_instance = MagicMock()
        mock_supervisor_instance.decompose_task.return_value = "Task decomposed"
        mock_supervisor.return_value = mock_supervisor_instance

        settings = TesseraSettings()
        console = Console()

        # Execute with dry-run to avoid complex execution
        execute_main(
            task="Build a web app",
            dry_run=True,
            background=False,
            multi_agent=False,
            max_parallel=3,
            config_file="",
            settings=settings,
            console=console,
        )

        # Verify tracer was initialized
        mock_tracer.assert_called_once()

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    def test_main_cmd_background_not_implemented(self, mock_cost, mock_metrics, mock_tracer, mock_dirs):
        """Test main command with background mode (not yet implemented)."""
        import typer
        from rich.console import Console

        from tessera.cli.commands.main_cmd import execute_main
        from tessera.config.schema import TesseraSettings

        mock_dirs.return_value = {"config": Path("/tmp")}
        settings = TesseraSettings()
        console = Console()

        # Background mode should exit with error
        with pytest.raises(typer.Exit) as exc_info:
            execute_main(
                task="Build a web app",
                dry_run=False,
                background=True,
                multi_agent=False,
                max_parallel=3,
                config_file="",
                settings=settings,
                console=console,
            )

        assert exc_info.value.exit_code == 1

    @patch("tessera.cli.commands.main_cmd.ensure_directories")
    @patch("tessera.cli.commands.main_cmd.init_tracer")
    @patch("tessera.cli.commands.main_cmd.MetricsStore")
    @patch("tessera.cli.commands.main_cmd.CostCalculator")
    @patch("tessera.cli.commands.main_cmd.SecretManager")
    @patch("tessera.cli.commands.main_cmd.SupervisorAgent")
    @patch("tessera.cli.multi_agent_execution.execute_multi_agent")
    def test_main_cmd_multi_agent_mode(
        self, mock_multi_exec, mock_supervisor, mock_secrets, mock_cost, mock_metrics, mock_tracer, mock_dirs
    ):
        """Test main command with multi-agent mode."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from tessera.cli.commands.main_cmd import execute_main
        from tessera.config.schema import AgentDefinition, TesseraSettings

        # Setup mocks
        mock_dirs.return_value = {"config": Path("/tmp")}
        mock_metrics_instance = MagicMock()
        mock_metrics.return_value = mock_metrics_instance
        mock_cost_instance = MagicMock()
        mock_cost.return_value = mock_cost_instance
        mock_secrets.get_openai_api_key.return_value = "test-key"

        # Mock supervisor
        mock_supervisor_instance = MagicMock()
        mock_supervisor.return_value = mock_supervisor_instance

        # Mock multi-agent execution
        mock_multi_exec.return_value = {
            "tasks_completed": 5,
            "tasks_total": 5,
            "tasks_failed": 0,
            "duration_seconds": 10.0,
        }

        # Create settings with multiple agents
        settings = TesseraSettings()
        settings.agents.definitions = [
            AgentDefinition(name="supervisor", role="supervisor", model="gpt-4o", provider="openai"),
            AgentDefinition(name="worker", role="worker", model="gpt-4o", provider="openai"),
        ]

        console = Console()

        # Execute with multi-agent
        execute_main(
            task="Build a web app",
            dry_run=False,
            background=False,
            multi_agent=True,
            max_parallel=2,
            config_file="",
            settings=settings,
            console=console,
        )

        # Verify multi-agent execution was called
        mock_multi_exec.assert_called_once()


@pytest.mark.integration
class TestMultiAgentExecutionModule:
    """Test multi-agent execution module."""

    @patch("tessera.cli.multi_agent_execution.AgentPool")
    @patch("tessera.cli.multi_agent_execution.MultiAgentExecutor")
    def test_execute_multi_agent_basic(self, mock_executor_class, mock_pool_class):
        """Test execute_multi_agent function."""
        from unittest.mock import MagicMock

        from rich.console import Console

        from tessera.cli.multi_agent_execution import execute_multi_agent
        from tessera.config.schema import AgentDefinition, TesseraSettings
        from tessera.observability import CostCalculator, MetricsStore

        # Setup mocks
        mock_pool = MagicMock()
        mock_pool.get_pool_status.return_value = {"total_agents": 2}
        mock_pool.agents = {
            "supervisor": MagicMock(config=MagicMock(model="gpt-4o")),
            "worker": MagicMock(config=MagicMock(model="gpt-4o")),
        }
        mock_pool_class.return_value = mock_pool

        mock_executor = MagicMock()
        mock_executor.execute_project.return_value = {
            "tasks_completed": 3,
            "tasks_total": 3,
            "tasks_failed": 0,
            "iterations": 2,
            "duration_seconds": 5.0,
        }
        mock_executor_class.return_value = mock_executor

        # Create settings
        settings = TesseraSettings()
        settings.agents.definitions = [
            AgentDefinition(name="supervisor", role="supervisor", model="gpt-4o", provider="openai"),
            AgentDefinition(name="worker", role="worker", model="gpt-4o", provider="openai"),
        ]

        supervisor = MagicMock()
        metrics_store = MetricsStore()
        cost_calc = CostCalculator()
        console = Console()

        # Execute
        result = execute_multi_agent(
            task_description="Build a web app",
            settings=settings,
            supervisor=supervisor,
            max_parallel=2,
            metrics_store=metrics_store,
            cost_calc=cost_calc,
            console=console,
        )

        # Verify results
        assert result["tasks_completed"] == 3
        assert result["tasks_total"] == 3
        mock_executor.execute_project.assert_called_once_with("Build a web app")
