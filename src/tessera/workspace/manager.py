"""
Workspace management for Tessera projects.

Manages project workspaces with directory tracking, archival, and global access.
"""

import json
import os
import shutil
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config.xdg import get_tessera_cache_dir, get_tessera_config_dir
from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Workspace:
    """Project workspace definition."""

    name: str
    path: Path
    created_at: datetime
    last_accessed: datetime
    archived: bool = False
    archive_path: Path | None = None
    metadata: dict[str, Any] | None = None


class WorkspaceManager:
    """
    Manages Tessera project workspaces.

    Features:
    - Track all accessed projects globally
    - Switch between workspaces with directory change
    - Archive/unarchive workspaces
    - Workspace-specific configuration and sandboxing
    """

    def __init__(self, storage_file: Path | None = None) -> None:
        """
        Initialize workspace manager.

        Args:
            storage_file: Workspace registry file
        """
        if storage_file is None:
            config_dir = get_tessera_config_dir()
            storage_file = config_dir / "workspaces.json"

        self.storage_file = storage_file
        self.archive_dir = get_tessera_cache_dir() / "workspace_archives"
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        self.workspaces: dict[str, Workspace] = {}
        self._load_workspaces()

        logger.debug(f"WorkspaceManager: {self.storage_file}")

    def _load_workspaces(self) -> None:
        """Load workspaces from storage."""
        if not self.storage_file.exists():
            self.workspaces = {}
            return

        try:
            with self.storage_file.open() as f:
                data = json.load(f)

            for name, ws_data in data.items():
                workspace = Workspace(
                    name=name,
                    path=Path(ws_data["path"]),
                    created_at=datetime.fromisoformat(ws_data["created_at"]),
                    last_accessed=datetime.fromisoformat(ws_data["last_accessed"]),
                    archived=ws_data.get("archived", False),
                    archive_path=Path(ws_data["archive_path"]) if ws_data.get("archive_path") else None,
                    metadata=ws_data.get("metadata"),
                )

                self.workspaces[name] = workspace

        except (OSError, ValueError) as e:
            logger.exception(f"Failed to load workspaces: {e}")
            self.workspaces = {}

    def _save_workspaces(self) -> None:
        """Save workspaces to storage."""
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

        data = {}

        for name, workspace in self.workspaces.items():
            data[name] = {
                "path": str(workspace.path),
                "created_at": workspace.created_at.isoformat(),
                "last_accessed": workspace.last_accessed.isoformat(),
                "archived": workspace.archived,
                "archive_path": str(workspace.archive_path) if workspace.archive_path else None,
                "metadata": workspace.metadata,
            }

        try:
            with self.storage_file.open("w") as f:
                json.dump(data, f, indent=2)

        except OSError as e:
            logger.exception(f"Failed to save workspaces: {e}")

    def register_workspace(
        self,
        name: str,
        path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> Workspace:
        """
        Register a new workspace.

        Args:
            name: Workspace name
            path: Project directory path
            metadata: Optional metadata

        Returns:
            Registered workspace
        """
        if name in self.workspaces:
            logger.warning(f"Workspace {name} already registered, updating")

        workspace = Workspace(
            name=name,
            path=path.resolve(),
            created_at=datetime.now(UTC),
            last_accessed=datetime.now(UTC),
            metadata=metadata,
        )

        self.workspaces[name] = workspace
        self._save_workspaces()

        logger.info(f"Registered workspace: {name} at {path}")

        return workspace

    def get_workspace(self, name: str) -> Workspace | None:
        """
        Get workspace by name.

        Args:
            name: Workspace name

        Returns:
            Workspace or None
        """
        workspace = self.workspaces.get(name)

        if workspace:
            # Update last accessed
            workspace.last_accessed = datetime.now(UTC)
            self._save_workspaces()

        return workspace

    def list_workspaces(self, include_archived: bool = False) -> list[Workspace]:
        """
        List all workspaces.

        Args:
            include_archived: Include archived workspaces

        Returns:
            List of workspaces
        """
        workspaces = list(self.workspaces.values())

        if not include_archived:
            workspaces = [w for w in workspaces if not w.archived]

        return sorted(workspaces, key=lambda w: w.last_accessed, reverse=True)

    def enter_workspace(self, name: str) -> bool:
        """
        Enter a workspace (change directory and setup).

        Args:
            name: Workspace name

        Returns:
            True if entered successfully
        """
        workspace = self.get_workspace(name)

        if workspace is None:
            logger.error(f"Workspace not found: {name}")
            return False

        if workspace.archived:
            logger.error(f"Workspace {name} is archived, unarchive first")
            return False

        if not workspace.path.exists():
            logger.error(f"Workspace path does not exist: {workspace.path}")
            return False

        # Change directory
        os.chdir(workspace.path)

        # Update last accessed
        workspace.last_accessed = datetime.now(UTC)
        self._save_workspaces()

        logger.info(f"Entered workspace: {name} at {workspace.path}")

        return True

    def archive_workspace(self, name: str) -> bool:
        """
        Archive a workspace.

        Args:
            name: Workspace name

        Returns:
            True if archived successfully
        """
        workspace = self.workspaces.get(name)

        if workspace is None:
            return False

        if workspace.archived:
            logger.warning(f"Workspace {name} already archived")
            return True

        # Create archive
        archive_name = f"{name}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.tar.gz"
        archive_path = self.archive_dir / archive_name

        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(workspace.path, arcname=name)

            workspace.archived = True
            workspace.archive_path = archive_path
            self._save_workspaces()

            logger.info(f"Archived workspace {name} to {archive_path}")

            return True

        except OSError as e:
            logger.exception(f"Failed to archive workspace {name}: {e}")
            return False

    def unarchive_workspace(self, name: str, extract_path: Path | None = None) -> bool:
        """
        Unarchive a workspace.

        Args:
            name: Workspace name
            extract_path: Where to extract (defaults to original path)

        Returns:
            True if unarchived successfully
        """
        workspace = self.workspaces.get(name)

        if workspace is None or not workspace.archived or not workspace.archive_path:
            return False

        extract_to = extract_path or workspace.path

        try:
            with tarfile.open(workspace.archive_path, "r:gz") as tar:
                # Safely extract with filter (Python 3.12+)
                tar.extractall(extract_to.parent, filter="data")

            workspace.archived = False
            workspace.path = extract_to
            self._save_workspaces()

            logger.info(f"Unarchived workspace {name} to {extract_to}")

            return True

        except OSError as e:
            logger.exception(f"Failed to unarchive workspace {name}: {e}")
            return False

    def delete_workspace(self, name: str, delete_files: bool = False) -> bool:
        """
        Delete workspace registration.

        Args:
            name: Workspace name
            delete_files: Also delete workspace files

        Returns:
            True if deleted
        """
        workspace = self.workspaces.get(name)

        if workspace is None:
            return False

        # Delete files if requested
        if delete_files and workspace.path.exists():
            try:
                shutil.rmtree(workspace.path)
                logger.info(f"Deleted workspace files: {workspace.path}")
            except OSError as e:
                logger.exception(f"Failed to delete workspace files: {e}")

        # Delete archive if exists
        if workspace.archive_path and workspace.archive_path.exists():
            try:
                workspace.archive_path.unlink()
            except OSError as e:
                logger.warning(f"Failed to delete archive: {e}")

        # Remove from registry
        del self.workspaces[name]
        self._save_workspaces()

        logger.info(f"Deleted workspace: {name}")

        return True

    def get_current_workspace(self) -> Workspace | None:
        """
        Get workspace for current directory.

        Returns:
            Workspace if current dir is in a workspace
        """
        cwd = Path.cwd().resolve()

        # Check if any workspace matches current directory or parent
        for workspace in self.workspaces.values():
            try:
                # Check if cwd is workspace dir or subdirectory
                cwd.relative_to(workspace.path)
                return workspace
            except ValueError:
                continue

        return None


# Global workspace manager
_workspace_manager: WorkspaceManager | None = None


def get_workspace_manager() -> WorkspaceManager:
    """
    Get global workspace manager.

    Returns:
        Global WorkspaceManager
    """
    global _workspace_manager

    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager()

    return _workspace_manager
