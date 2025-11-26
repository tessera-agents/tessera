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
                # Resolve both paths to handle macOS /var -> /private/var symlink
                assert Path.cwd().resolve() == ws_path.resolve()

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

    def test_get_current_workspace(self):
        """Test getting workspace for current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            import os

            original_cwd = Path.cwd()

            try:
                # Change to workspace directory
                os.chdir(ws_path)

                # Should find the current workspace
                current = manager.get_current_workspace()
                assert current is not None
                assert current.name == "test"

            finally:
                os.chdir(original_cwd)

    def test_get_workspace_manager_singleton(self):
        """Test get_workspace_manager returns singleton."""
        from tessera.workspace.manager import get_workspace_manager

        manager1 = get_workspace_manager()
        manager2 = get_workspace_manager()

        # Should return same instance
        assert manager1 is manager2

    def test_load_workspaces_error_handling(self, mocker):
        """Test error handling when loading workspaces fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = Path(tmpdir) / "workspaces.json"
            # Create a corrupted JSON file
            storage_file.write_text("{invalid json}")

            # Should handle error gracefully
            manager = WorkspaceManager(storage_file)

            assert manager.workspaces == {}

    def test_load_workspaces_oserror(self, mocker):
        """Test OSError handling when loading workspaces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = Path(tmpdir) / "workspaces.json"

            # Mock Path.open to raise OSError before we try to create the manager
            original_open = Path.open

            def mock_open_func(self, *args, **kwargs):
                if self == storage_file and args and args[0] != "w":
                    raise OSError("Permission denied")
                return original_open(self, *args, **kwargs)

            mocker.patch.object(Path, "open", mock_open_func)

            manager = WorkspaceManager(storage_file)

            assert manager.workspaces == {}

    def test_save_workspaces_error_handling(self, mocker):
        """Test error handling when saving workspaces fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = Path(tmpdir) / "workspaces.json"
            manager = WorkspaceManager(storage_file)

            # Add a workspace
            manager.register_workspace("test", Path(tmpdir))

            # Mock json.dump to raise OSError
            mock_dump = mocker.patch("json.dump", side_effect=OSError("Disk full"))

            # Should handle error gracefully
            manager._save_workspaces()

            mock_dump.assert_called_once()

    def test_register_workspace_existing_warning(self):
        """Test registering an already existing workspace logs warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            # Register workspace
            ws1 = manager.register_workspace("test", Path(tmpdir) / "ws1")
            assert ws1.name == "test"

            # Register again with different path (should update)
            ws2 = manager.register_workspace("test", Path(tmpdir) / "ws2")
            assert ws2.name == "test"
            assert ws2.path == (Path(tmpdir) / "ws2").resolve()

    def test_get_workspace_updates_last_accessed(self):
        """Test get_workspace updates last_accessed timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            # Register workspace
            ws = manager.register_workspace("test", Path(tmpdir))
            original_time = ws.last_accessed

            # Wait a moment and get workspace again
            import time

            time.sleep(0.01)

            retrieved = manager.get_workspace("test")

            assert retrieved is not None
            assert retrieved.last_accessed > original_time

    def test_get_workspace_none(self):
        """Test get_workspace returns None for non-existent workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            result = manager.get_workspace("nonexistent")

            assert result is None

    def test_list_workspaces_exclude_archived(self):
        """Test list_workspaces excludes archived by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            # Create workspaces
            manager.register_workspace("active", Path(tmpdir) / "active")
            ws_archived = manager.register_workspace("archived", Path(tmpdir) / "archived")

            # Manually mark as archived
            ws_archived.archived = True
            manager._save_workspaces()

            # List without archived
            workspaces = manager.list_workspaces(include_archived=False)

            assert len(workspaces) == 1
            assert workspaces[0].name == "active"

    def test_list_workspaces_include_archived(self):
        """Test list_workspaces includes archived when requested."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            # Create workspaces
            manager.register_workspace("active", Path(tmpdir) / "active")
            ws_archived = manager.register_workspace("archived", Path(tmpdir) / "archived")

            # Manually mark as archived
            ws_archived.archived = True
            manager._save_workspaces()

            # List with archived
            workspaces = manager.list_workspaces(include_archived=True)

            assert len(workspaces) == 2

    def test_enter_workspace_not_found(self):
        """Test enter_workspace returns False for non-existent workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            result = manager.enter_workspace("nonexistent")

            assert result is False

    def test_enter_workspace_archived(self):
        """Test enter_workspace returns False for archived workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            ws = manager.register_workspace("test", ws_path)

            # Mark as archived
            ws.archived = True
            manager._save_workspaces()

            result = manager.enter_workspace("test")

            assert result is False

    def test_enter_workspace_path_not_exists(self):
        """Test enter_workspace returns False when path doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            # Register workspace with non-existent path
            manager.register_workspace("test", Path(tmpdir) / "nonexistent")

            result = manager.enter_workspace("test")

            assert result is False

    def test_archive_workspace_success(self):
        """Test successful workspace archival."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()
            (ws_path / "file.txt").write_text("test content")

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            # Archive workspace
            result = manager.archive_workspace("test")

            assert result is True

            # Check workspace is marked as archived
            ws = manager.get_workspace("test")
            assert ws.archived is True
            assert ws.archive_path is not None
            assert ws.archive_path.exists()

    def test_archive_workspace_not_found(self):
        """Test archive_workspace returns False for non-existent workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            result = manager.archive_workspace("nonexistent")

            assert result is False

    def test_archive_workspace_already_archived(self):
        """Test archive_workspace handles already archived workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            ws = manager.register_workspace("test", ws_path)

            # Mark as already archived
            ws.archived = True
            ws.archive_path = Path(tmpdir) / "test.tar.gz"
            manager._save_workspaces()

            result = manager.archive_workspace("test")

            # Should return True (already archived)
            assert result is True

    def test_archive_workspace_error(self, mocker):
        """Test archive_workspace handles tarfile errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            # Mock tarfile.open to raise OSError
            mock_tarfile = mocker.patch("tarfile.open", side_effect=OSError("Cannot create archive"))

            result = manager.archive_workspace("test")

            assert result is False
            mock_tarfile.assert_called_once()

            # Workspace should not be marked as archived
            ws = manager.get_workspace("test")
            assert ws.archived is False

    def test_unarchive_workspace_success(self, mocker):
        """Test successful workspace unarchival."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()
            (ws_path / "file.txt").write_text("test content")

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            # Archive first
            manager.archive_workspace("test")

            # Delete the original directory
            import shutil

            shutil.rmtree(ws_path)

            # Unarchive
            result = manager.unarchive_workspace("test")

            assert result is True

            # Check workspace is no longer archived
            ws = manager.get_workspace("test")
            assert ws.archived is False
            # Check that the path was extracted (it should exist now)
            assert (Path(tmpdir) / "test").exists()  # Archive extracts to parent with name

    def test_unarchive_workspace_not_found(self):
        """Test unarchive_workspace returns False for non-existent workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            result = manager.unarchive_workspace("nonexistent")

            assert result is False

    def test_unarchive_workspace_not_archived(self):
        """Test unarchive_workspace returns False for non-archived workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            result = manager.unarchive_workspace("test")

            assert result is False

    def test_unarchive_workspace_custom_path(self, mocker):
        """Test unarchive_workspace with custom extraction path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()
            (ws_path / "file.txt").write_text("test content")

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            # Archive
            manager.archive_workspace("test")

            # Unarchive to custom path
            custom_path = Path(tmpdir) / "custom_location" / "workspace"
            result = manager.unarchive_workspace("test", custom_path)

            assert result is True

            ws = manager.get_workspace("test")
            assert ws.path == custom_path

    def test_unarchive_workspace_error(self, mocker):
        """Test unarchive_workspace handles tarfile errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            ws = manager.register_workspace("test", ws_path)

            # Manually set as archived
            ws.archived = True
            ws.archive_path = Path(tmpdir) / "test.tar.gz"
            manager._save_workspaces()

            # Mock tarfile.open to raise OSError
            mock_tarfile = mocker.patch("tarfile.open", side_effect=OSError("Cannot extract archive"))

            result = manager.unarchive_workspace("test")

            assert result is False
            mock_tarfile.assert_called_once()

            # Workspace should still be marked as archived
            ws = manager.get_workspace("test")
            assert ws.archived is True

    def test_delete_workspace_success(self):
        """Test successful workspace deletion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            result = manager.delete_workspace("test", delete_files=False)

            assert result is True
            assert "test" not in manager.workspaces
            assert ws_path.exists()  # Files should still exist

    def test_delete_workspace_with_files(self):
        """Test workspace deletion with file removal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()
            (ws_path / "file.txt").write_text("test")

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            result = manager.delete_workspace("test", delete_files=True)

            assert result is True
            assert "test" not in manager.workspaces
            assert not ws_path.exists()

    def test_delete_workspace_not_found(self):
        """Test delete_workspace returns False for non-existent workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")

            result = manager.delete_workspace("nonexistent")

            assert result is False

    def test_delete_workspace_with_archive(self):
        """Test delete_workspace removes archive if it exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()
            (ws_path / "file.txt").write_text("test")

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            # Archive workspace
            manager.archive_workspace("test")

            ws = manager.get_workspace("test")
            archive_path = ws.archive_path

            assert archive_path.exists()

            # Delete workspace
            result = manager.delete_workspace("test")

            assert result is True
            assert not archive_path.exists()

    def test_delete_workspace_files_error(self, mocker):
        """Test delete_workspace handles file deletion errors."""
        import shutil

        ws_path = None
        manager = None
        tmpdir_obj = tempfile.TemporaryDirectory()

        try:
            tmpdir = tmpdir_obj.name
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            # Store original rmtree
            original_rmtree = shutil.rmtree

            # Create selective mock that only fails for our workspace path
            def selective_rmtree(path, *args, **kwargs):
                if Path(path) == ws_path:
                    raise OSError("Permission denied")
                return original_rmtree(path, *args, **kwargs)

            mock_rmtree = mocker.patch("tessera.workspace.manager.shutil.rmtree", side_effect=selective_rmtree)

            result = manager.delete_workspace("test", delete_files=True)

            # Should still delete from registry even when file deletion fails
            assert result is True
            assert "test" not in manager.workspaces
            # rmtree should have been called (even though it failed)
            assert mock_rmtree.called

        finally:
            # Restore original before cleanup
            if mocker:
                mocker.stopall()
            tmpdir_obj.cleanup()

    def test_delete_workspace_archive_error(self, mocker):
        """Test delete_workspace handles archive deletion errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            ws = manager.register_workspace("test", ws_path)

            # Manually set archive path
            archive_path = Path(tmpdir) / "test.tar.gz"
            archive_path.write_text("fake archive")
            ws.archive_path = archive_path
            manager._save_workspaces()

            # Mock unlink to raise OSError
            mocker.patch.object(Path, "unlink", side_effect=OSError("Permission denied"))

            result = manager.delete_workspace("test")

            # Should still delete from registry
            assert result is True
            assert "test" not in manager.workspaces

    def test_get_current_workspace_no_match(self):
        """Test get_current_workspace returns None when no workspace matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            # Current directory is not in workspace
            current = manager.get_current_workspace()

            # Should not match
            assert current is None or current.name != "test"

    def test_get_current_workspace_in_subdirectory(self):
        """Test get_current_workspace finds workspace from subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws_path = Path(tmpdir) / "workspace"
            ws_path.mkdir()
            subdir = ws_path / "subdir"
            subdir.mkdir()

            manager = WorkspaceManager(Path(tmpdir) / "workspaces.json")
            manager.register_workspace("test", ws_path)

            import os

            original_cwd = Path.cwd()

            try:
                # Change to subdirectory
                os.chdir(subdir)

                # Should find the parent workspace
                current = manager.get_current_workspace()
                assert current is not None
                assert current.name == "test"

            finally:
                os.chdir(original_cwd)


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
