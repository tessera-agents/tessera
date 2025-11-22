"""
Tests for CLI module.
"""

import pytest
from unittest.mock import patch, Mock
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
        assert hasattr(settings, 'tessera')
        assert hasattr(settings, 'agents')


@pytest.mark.unit
class TestMultiAgentExecution:
    """Test multi-agent execution helper."""

    def test_module_exists(self):
        """Test multi_agent_execution module imports."""
        from tessera.cli import multi_agent_execution
        assert multi_agent_execution is not None
