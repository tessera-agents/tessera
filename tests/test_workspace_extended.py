"""Extended tests for workspace management and sandboxing."""

import tempfile
from pathlib import Path

import pytest

from tessera.workspace.filesystem_protection import (
    FilesystemGuard,
    PathPermission,
    check_path_access,
)
from tessera.workspace.sandbox import Sandbox, SandboxConfig, create_sandbox


@pytest.mark.unit
class TestFilesystemGuardExtended:
    """Extended tests for filesystem protection."""

    def test_check_operation_logs_blocking(self):
        """Test check_operation method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()
            outside_file = Path(tmpdir) / "outside.txt"

            guard = FilesystemGuard(workspace)
            allowed, reason = guard.check_operation(outside_file, PathPermission.READ)

            assert allowed is False
            assert reason == "outside_workspace"

    def test_get_safe_path_valid(self):
        """Test getting safe path for valid path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            test_file = workspace / "test.txt"

            guard = FilesystemGuard(workspace)
            safe_path = guard.get_safe_path(str(test_file))

            assert safe_path is not None
            assert safe_path.resolve() == test_file.resolve()

    def test_get_safe_path_invalid(self):
        """Test get_safe_path returns None for blocked path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()
            outside_file = Path(tmpdir) / "outside.txt"

            guard = FilesystemGuard(workspace)
            safe_path = guard.get_safe_path(str(outside_file))

            assert safe_path is None

    def test_list_allowed_directories(self):
        """Test listing allowed directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            extra_path = Path(tmpdir) / "extra"

            guard = FilesystemGuard(workspace, allowed_paths=[extra_path])
            allowed = guard.list_allowed_directories()

            assert len(allowed) >= 2
            assert workspace.resolve() in allowed

    def test_block_path(self):
        """Test blocking a path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            block_path = workspace / "blocked"

            guard = FilesystemGuard(workspace)

            # Initially allowed
            allowed, _ = guard.is_path_allowed(block_path, PathPermission.READ)
            assert allowed is True

            # Block the path
            guard.block_path(block_path)
            allowed, reason = guard.is_path_allowed(block_path, PathPermission.READ)

            assert allowed is False
            assert "blocked_path" in reason

    def test_cannot_remove_workspace_root(self):
        """Test that workspace root cannot be removed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            guard = FilesystemGuard(workspace)

            result = guard.remove_allowed_path(workspace)

            assert result is False
            assert workspace.resolve() in guard.allowed_paths

    def test_check_path_access_function(self):
        """Test standalone check_path_access function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            test_file = workspace / "test.txt"

            allowed, reason = check_path_access(test_file, PathPermission.READ, workspace)

            assert allowed is True
            assert reason == "allowed"

    def test_invalid_path_handling(self):
        """Test handling of invalid paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            guard = FilesystemGuard(workspace)

            # Try to use an invalid path string
            safe_path = guard.get_safe_path("\x00invalid")

            assert safe_path is None

    def test_critical_file_delete_blocked(self):
        """Test deleting critical files is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            env_file = workspace / ".env"

            guard = FilesystemGuard(workspace)
            allowed, reason = guard.is_path_allowed(env_file, PathPermission.DELETE)

            assert allowed is False
            assert "critical_file" in reason

    def test_additional_allowed_paths(self):
        """Test initialization with additional allowed paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()
            extra = Path(tmpdir) / "extra"
            extra.mkdir()

            guard = FilesystemGuard(workspace, allowed_paths=[extra])

            # Both should be allowed
            allowed1, _ = guard.is_path_allowed(workspace / "file.txt", PathPermission.READ)
            allowed2, _ = guard.is_path_allowed(extra / "file.txt", PathPermission.READ)

            assert allowed1 is True
            assert allowed2 is True

    def test_blocked_paths_initialization(self):
        """Test initialization with blocked paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            blocked = workspace / "blocked"

            guard = FilesystemGuard(workspace, blocked_paths=[blocked])

            allowed, reason = guard.is_path_allowed(blocked / "file.txt", PathPermission.READ)

            assert allowed is False
            assert "blocked_path" in reason


@pytest.mark.unit
class TestSandboxExtended:
    """Extended tests for sandboxing."""

    def test_sandbox_enter_exit(self, mocker):
        """Test sandbox enter/exit resource limits."""
        # Mock both resource.setrlimit and os.chdir to test without side effects
        mock_setrlimit = mocker.patch("resource.setrlimit")
        mock_chdir = mocker.patch("os.chdir")

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            sandbox = create_sandbox(workspace)

            sandbox.enter()

            assert sandbox.active is True
            # Verify resource limits were set
            assert mock_setrlimit.call_count > 0
            # Verify chdir was called
            mock_chdir.assert_called_with(workspace)

            sandbox.exit()

            assert sandbox.active is False

    def test_sandbox_enter_already_active(self, mocker):
        """Test entering an already active sandbox."""
        # Mock both resource.setrlimit and os.chdir to test without side effects
        mocker.patch("resource.setrlimit")
        mocker.patch("os.chdir")

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            sandbox = create_sandbox(workspace)

            sandbox.enter()
            assert sandbox.active is True

            # Try to enter again - should log warning but not error
            sandbox.enter()
            assert sandbox.active is True

            sandbox.exit()

    def test_sandbox_exit_not_active(self):
        """Test exiting an inactive sandbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            sandbox = create_sandbox(workspace)

            # Exit without entering - should not error
            sandbox.exit()

            assert sandbox.active is False

    def test_sandbox_execute_sandboxed(self, mocker):
        """Test executing command in sandbox."""
        mocker.patch("resource.setrlimit")
        mocker.patch("os.chdir")

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            sandbox = create_sandbox(workspace)

            sandbox.enter()

            # Execute a simple command
            result = sandbox.execute_sandboxed(["echo", "test"])

            assert result.returncode == 0
            assert "test" in result.stdout

            sandbox.exit()

    def test_sandbox_execute_with_env(self, mocker):
        """Test executing command with custom environment."""
        mocker.patch("resource.setrlimit")
        mocker.patch("os.chdir")

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            sandbox = create_sandbox(workspace)

            sandbox.enter()

            # Execute with custom env
            import platform

            if platform.system() != "Windows":
                result = sandbox.execute_sandboxed(["sh", "-c", "echo $TEST_VAR"], env={"TEST_VAR": "custom_value"})

                assert result.returncode == 0
                assert "custom_value" in result.stdout

            sandbox.exit()

    def test_sandbox_network_restriction(self, mocker):
        """Test network access restriction."""
        mocker.patch("resource.setrlimit")
        mocker.patch("os.chdir")

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            config = SandboxConfig(workspace_root=workspace, network_access=False)
            sandbox = Sandbox(config)

            sandbox.enter()

            # Execute a command - should have network proxy set
            import platform

            if platform.system() != "Windows":
                result = sandbox.execute_sandboxed(["sh", "-c", "echo $http_proxy"])

                assert result.returncode == 0
                # Should have proxy set to block network
                assert "127.0.0.1:1" in result.stdout

            sandbox.exit()

    def test_sandbox_execute_not_active(self):
        """Test executing in inactive sandbox logs warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            sandbox = create_sandbox(workspace)

            # Execute without entering - should work but log warning
            result = sandbox.execute_sandboxed(["echo", "test"])

            assert result.returncode == 0

    def test_sandbox_execute_with_custom_cwd(self, mocker):
        """Test executing with custom working directory."""
        mocker.patch("resource.setrlimit")
        mocker.patch("os.chdir")

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            subdir = workspace / "subdir"
            subdir.mkdir()

            sandbox = create_sandbox(workspace)

            sandbox.enter()

            # Execute with custom cwd
            import platform

            if platform.system() != "Windows":
                result = sandbox.execute_sandboxed(["pwd"], cwd=subdir)

                assert result.returncode == 0

            sandbox.exit()
