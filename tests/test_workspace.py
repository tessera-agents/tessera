"""Tests for workspace management and sandboxing."""

import tempfile
from pathlib import Path

import pytest

from tessera.workspace.filesystem_protection import (
    FilesystemGuard,
    PathPermission,
)
from tessera.workspace.manager import WorkspaceManager
from tessera.workspace.sandbox import Sandbox, SandboxConfig, create_sandbox


@pytest.mark.unit
class TestWorkspaceManager:
    """Test workspace manager."""

    def test_manager_initialization(self):
        """Test workspace manager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = Path(tmpdir) / "workspaces.json"
            manager = WorkspaceManager(storage_file)

            assert manager.storage_file == storage_file
            assert manager.workspaces == {}

    def test_register_workspace(self):
        """Test registering new workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            workspace = manager.register_workspace("test-project", Path(tmpdir) / "project")

            assert workspace.name == "test-project"
            assert "test-project" in manager.workspaces

    def test_get_workspace(self):
        """Test getting workspace by name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            _ = manager.register_workspace("test", Path(tmpdir))

            retrieved = manager.get_workspace("test")

            assert retrieved is not None
            assert retrieved.name == "test"

    def test_list_workspaces(self):
        """Test listing workspaces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            manager.register_workspace("ws1", Path(tmpdir) / "ws1")
            manager.register_workspace("ws2", Path(tmpdir) / "ws2")

            workspaces = manager.list_workspaces()

            assert len(workspaces) == 2

    def test_enter_workspace(self):
        """Test entering workspace changes directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            original_cwd = Path.cwd()

            try:
                success = manager.enter_workspace("test")

                assert success is True
                assert Path.cwd() == ws_path

            finally:
                import os

                os.chdir(original_cwd)

    def test_workspace_persistence(self):
        """Test workspaces persist across manager instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = Path(tmpdir) / "workspaces.json"

            # First manager
            manager1 = WorkspaceManager(storage_file)
            manager1.register_workspace("persistent", Path(tmpdir) / "ws")

            # Second manager (should load from disk)
            manager2 = WorkspaceManager(storage_file)

            assert "persistent" in manager2.workspaces


@pytest.mark.unit
class TestFilesystemGuard:
    """Test filesystem protection."""

    def test_guard_initialization(self):
        """Test guard initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            guard = FilesystemGuard(workspace)

            assert workspace.resolve() in guard.allowed_paths

    def test_path_allowed_in_workspace(self):
        """Test path within workspace is allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            test_file = workspace / "test.txt"

            guard = FilesystemGuard(workspace)
            allowed, reason = guard.is_path_allowed(test_file, PathPermission.READ)

            assert allowed is True
            assert reason == "allowed"

    def test_path_blocked_outside_workspace(self):
        """Test path outside workspace is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()

            outside_file = Path(tmpdir) / "outside.txt"

            guard = FilesystemGuard(workspace)
            allowed, reason = guard.is_path_allowed(outside_file, PathPermission.READ)

            assert allowed is False
            assert "outside_workspace" in reason

    def test_sensitive_directory_blocked(self):
        """Test sensitive directories are blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            guard = FilesystemGuard(workspace)

            # Try to access .ssh
            ssh_dir = Path.home() / ".ssh" / "id_rsa"
            allowed, reason = guard.is_path_allowed(ssh_dir, PathPermission.READ)

            assert allowed is False
            assert "blocked_path" in reason

    def test_critical_file_write_blocked(self):
        """Test writing to critical files is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            git_dir = workspace / ".git"

            guard = FilesystemGuard(workspace)
            allowed, reason = guard.is_path_allowed(git_dir, PathPermission.WRITE)

            assert allowed is False
            assert "critical_file" in reason

    def test_add_remove_allowed_paths(self):
        """Test dynamically adding/removing allowed paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            workspace.mkdir()

            extra_path = Path(tmpdir) / "extra"
            extra_path.mkdir()

            guard = FilesystemGuard(workspace)

            # Initially blocked
            allowed, _ = guard.is_path_allowed(extra_path / "file.txt", PathPermission.READ)
            assert allowed is False

            # Add to allowed
            guard.add_allowed_path(extra_path)
            allowed, _ = guard.is_path_allowed(extra_path / "file.txt", PathPermission.READ)
            assert allowed is True

            # Remove
            guard.remove_allowed_path(extra_path)
            allowed, _ = guard.is_path_allowed(extra_path / "file.txt", PathPermission.READ)
            assert allowed is False


@pytest.mark.unit
class TestSandbox:
    """Test sandboxing."""

    def test_sandbox_initialization(self):
        """Test sandbox initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            config = SandboxConfig(workspace_root=workspace)

            sandbox = Sandbox(config)

            assert sandbox.config == config
            assert sandbox.active is False

    def test_sandbox_context_manager(self):
        """Test sandbox as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            sandbox = create_sandbox(workspace)

            assert sandbox.active is False

            with sandbox:
                assert sandbox.active is True

            assert sandbox.active is False

    def test_create_sandbox_strict(self):
        """Test creating strict sandbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            sandbox = create_sandbox(workspace, strict=True)

            assert sandbox.config.max_memory_mb == 1024
            assert sandbox.config.network_access is False

    def test_create_sandbox_permissive(self):
        """Test creating permissive sandbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            sandbox = create_sandbox(workspace, strict=False)

            assert sandbox.config.max_memory_mb == 4096
            assert sandbox.config.network_access is True

    def test_sandbox_get_stats(self):
        """Test sandbox statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            sandbox = create_sandbox(workspace)

            stats = sandbox.get_stats()

            assert stats["active"] is False
            assert "workspace_root" in stats
            assert "max_memory_mb" in stats
