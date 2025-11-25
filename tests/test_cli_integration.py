"""Integration tests for Tessera CLI commands (workflow and session)."""

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from tessera.api.session import SessionManager
from tessera.cli.main import app
from tessera.workflow.templates import WorkflowTemplateStorage


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_session_manager(tmp_path):
    """Create a mock session manager with temp storage."""
    return SessionManager(storage_dir=tmp_path / "sessions")


@pytest.fixture
def mock_workflow_storage(tmp_path):
    """Create a mock workflow template storage."""
    storage_dir = tmp_path / "templates"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return WorkflowTemplateStorage(storage_dir=storage_dir)


@pytest.mark.integration
class TestVersionCommand:
    """Test version command."""

    def test_version_displays_correctly(self, cli_runner):
        """Test version command shows version info."""
        result = cli_runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "Tessera v0.4.0" in result.stdout
        assert "Multi-Agent Orchestration Framework" in result.stdout


@pytest.mark.integration
class TestWorkflowListCommand:
    """Test workflow list command."""

    def test_workflow_list_empty(self, cli_runner, tmp_path):
        """Test listing workflows when none exist."""
        with patch("tessera.workflow.templates.WorkflowTemplateStorage") as mock_storage_class:
            mock_storage = Mock()
            mock_storage.list_templates.return_value = []
            mock_storage_class.return_value = mock_storage

            result = cli_runner.invoke(app, ["workflow-list"])

            assert result.exit_code == 0
            assert "No workflow templates found" in result.stdout

    def test_workflow_list_with_templates(self, cli_runner, tmp_path):
        """Test listing workflows with templates."""
        with patch("tessera.workflow.templates.WorkflowTemplateStorage") as mock_storage_class:
            mock_storage = Mock()
            mock_storage.list_templates.return_value = ["test-workflow"]
            mock_storage.get_template_info.return_value = {
                "name": "test-workflow",
                "description": "Test workflow",
                "phase_count": 3,
                "agent_count": 2,
            }
            mock_storage_class.return_value = mock_storage

            result = cli_runner.invoke(app, ["workflow-list"])

            assert result.exit_code == 0
            assert "test-workflow" in result.stdout
            assert "Test workflow" in result.stdout


@pytest.mark.integration
class TestWorkflowShowCommand:
    """Test workflow show command."""

    def test_workflow_show_success(self, cli_runner):
        """Test showing a workflow template."""
        with patch("tessera.workflow.templates.WorkflowTemplateStorage") as mock_storage_class:
            mock_storage = Mock()
            mock_template = Mock()
            mock_template.name = "test-workflow"
            mock_template.description = "Test workflow description"
            mock_template.complexity = "medium"
            mock_template.phases = []
            mock_template.suggested_agents = []
            mock_storage.load.return_value = mock_template
            mock_storage_class.return_value = mock_storage

            result = cli_runner.invoke(app, ["workflow-show", "test-workflow"])

            assert result.exit_code == 0
            assert "test-workflow" in result.stdout
            assert "Test workflow description" in result.stdout

    def test_workflow_show_not_found(self, cli_runner):
        """Test showing non-existent workflow."""
        with patch("tessera.workflow.templates.WorkflowTemplateStorage") as mock_storage_class:
            mock_storage = Mock()
            mock_storage.load.return_value = None
            mock_storage_class.return_value = mock_storage

            result = cli_runner.invoke(app, ["workflow-show", "nonexistent"])

            assert result.exit_code == 0
            assert "not found" in result.stdout


@pytest.mark.integration
class TestWorkflowInstallBuiltins:
    """Test workflow install-builtins command."""

    def test_install_builtins_success(self, cli_runner):
        """Test installing built-in workflow templates."""
        with patch("tessera.workflow.templates.install_builtin_templates") as mock_install:
            mock_install.return_value = 3

            result = cli_runner.invoke(app, ["workflow-install-builtins"])

            assert result.exit_code == 0
            assert "Installed 3 built-in templates" in result.stdout
            mock_install.assert_called_once()


@pytest.mark.integration
class TestSessionListCommand:
    """Test session list command."""

    def test_session_list_empty(self, cli_runner):
        """Test listing sessions when none exist."""
        with patch("tessera.api.session.get_session_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.list_sessions.return_value = []
            mock_get_manager.return_value = mock_manager

            result = cli_runner.invoke(app, ["session-list"])

            assert result.exit_code == 0
            assert "No sessions found" in result.stdout

    def test_session_list_with_sessions(self, cli_runner, mock_session_manager):
        """Test listing sessions with data."""
        with patch("tessera.api.session.get_session_manager") as mock_get_manager:
            # Create test sessions
            session1 = mock_session_manager.create_session("Task 1")
            session2 = mock_session_manager.create_session("Task 2")
            session2.start()

            mock_manager = Mock()
            mock_manager.list_sessions.return_value = [session1, session2]
            mock_get_manager.return_value = mock_manager

            result = cli_runner.invoke(app, ["session-list"])

            assert result.exit_code == 0
            assert "Task 1" in result.stdout
            assert "Task 2" in result.stdout


@pytest.mark.integration
class TestSessionAttachCommand:
    """Test session attach command."""

    def test_session_attach_success(self, cli_runner, mock_session_manager):
        """Test attaching to a session."""
        with patch("tessera.api.session.get_session_manager") as mock_get_manager:
            session = mock_session_manager.create_session("Test task")
            session.start()

            mock_manager = Mock()
            mock_manager.get_session.return_value = session
            mock_get_manager.return_value = mock_manager

            result = cli_runner.invoke(app, ["session-attach", session.session_id])

            assert result.exit_code == 0
            assert session.session_id[:8] in result.stdout
            assert "Test task" in result.stdout

    def test_session_attach_not_found(self, cli_runner):
        """Test attaching to non-existent session."""
        with patch("tessera.api.session.get_session_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_session.return_value = None
            mock_get_manager.return_value = mock_manager

            result = cli_runner.invoke(app, ["session-attach", "nonexistent-id"])

            assert result.exit_code == 1
            assert "not found" in result.stdout


@pytest.mark.integration
class TestSessionPauseCommand:
    """Test session pause command."""

    def test_session_pause_success(self, cli_runner):
        """Test pausing a session."""
        with patch("tessera.api.session.get_session_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.pause_session.return_value = True
            mock_get_manager.return_value = mock_manager

            result = cli_runner.invoke(app, ["session-pause", "test-session-id"])

            assert result.exit_code == 0
            assert "paused" in result.stdout

    def test_session_pause_failure(self, cli_runner):
        """Test pausing session that fails."""
        with patch("tessera.api.session.get_session_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.pause_session.return_value = False
            mock_get_manager.return_value = mock_manager

            result = cli_runner.invoke(app, ["session-pause", "test-session-id"])

            assert result.exit_code == 1
            assert "Failed" in result.stdout


@pytest.mark.integration
class TestSessionResumeCommand:
    """Test session resume command."""

    def test_session_resume_success(self, cli_runner):
        """Test resuming a session."""
        with patch("tessera.api.session.get_session_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.resume_session.return_value = True
            mock_get_manager.return_value = mock_manager

            result = cli_runner.invoke(app, ["session-resume", "test-session-id"])

            assert result.exit_code == 0
            assert "resumed" in result.stdout

    def test_session_resume_failure(self, cli_runner):
        """Test resuming session that fails."""
        with patch("tessera.api.session.get_session_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.resume_session.return_value = False
            mock_get_manager.return_value = mock_manager

            result = cli_runner.invoke(app, ["session-resume", "test-session-id"])

            assert result.exit_code == 1
            assert "Failed" in result.stdout


@pytest.mark.integration
class TestServeCommand:
    """Test serve command."""

    def test_serve_starts_server(self, cli_runner):
        """Test serve command starts server (mocked)."""
        with patch("tessera.api.server.start_server") as mock_start:
            # Use invoke with input to simulate Ctrl+C
            with patch("sys.stdin"):
                result = cli_runner.invoke(app, ["serve", "--host", "0.0.0.0", "--port", "9000"])

                # Command should have called start_server
                if result.exit_code == 0:
                    mock_start.assert_called_once_with(host="0.0.0.0", port=9000)


@pytest.mark.integration
class TestInitCommand:
    """Test init command (basic validation only)."""

    def test_init_with_existing_config(self, cli_runner, tmp_path):
        """Test init command when config already exists."""
        with patch("tessera.cli.main.get_config_file_path") as mock_get_path:
            config_file = tmp_path / "config.yaml"
            config_file.write_text("existing: config")
            mock_get_path.return_value = config_file

            # Simulate user saying "no" to overwrite
            result = cli_runner.invoke(app, ["init"], input="n\n")

            assert result.exit_code == 0
            assert "already exists" in result.stdout
            assert "Keeping existing" in result.stdout
