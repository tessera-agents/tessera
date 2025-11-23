"""
Filesystem protection for workspace operations.

Implements permission system to protect filesystem from unauthorized access.
"""

from enum import Enum
from pathlib import Path

from ..logging_config import get_logger

logger = get_logger(__name__)


class PathPermission(Enum):
    """Filesystem permissions."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"


class FilesystemGuard:
    """
    Protects filesystem with permission checks.

    Prevents agents from accessing files outside allowed paths.
    """

    def __init__(
        self,
        workspace_root: Path,
        allowed_paths: list[Path] | None = None,
        blocked_paths: list[Path] | None = None,
    ) -> None:
        """
        Initialize filesystem guard.

        Args:
            workspace_root: Workspace root directory (always allowed)
            allowed_paths: Additional allowed paths
            blocked_paths: Explicitly blocked paths (even within workspace)
        """
        self.workspace_root = workspace_root.resolve()
        self.allowed_paths = [p.resolve() for p in (allowed_paths or [])]
        self.blocked_paths = [p.resolve() for p in (blocked_paths or [])]

        # Always allow workspace root
        if self.workspace_root not in self.allowed_paths:
            self.allowed_paths.append(self.workspace_root)

        # Block common sensitive directories
        self.blocked_paths.extend(
            [
                Path.home() / ".ssh",
                Path.home() / ".aws",
                Path.home() / ".config" / "gcloud",
                Path("/etc"),
                Path("/var"),
                Path("/sys"),
            ]
        )

        logger.debug(f"FilesystemGuard initialized for {workspace_root}")

    def is_path_allowed(
        self,
        path: Path,
        permission: PathPermission = PathPermission.READ,
    ) -> tuple[bool, str]:
        """
        Check if path access is allowed.

        Args:
            path: Path to check
            permission: Required permission

        Returns:
            Tuple of (allowed, reason)
        """
        try:
            path = path.resolve()
        except Exception as e:
            return (False, f"invalid_path: {e}")

        # Check blocked paths first
        for blocked in self.blocked_paths:
            try:
                path.relative_to(blocked)
                return (False, f"blocked_path: {blocked}")
            except ValueError:
                pass  # Not in blocked path

        # Check if within allowed paths
        for allowed in self.allowed_paths:
            try:
                path.relative_to(allowed)

                # Additional checks for write/delete permissions
                if permission in (PathPermission.WRITE, PathPermission.DELETE):
                    # Check if trying to modify critical files
                    if path.name in [".git", ".env", "credentials.json", "secrets.yaml"]:
                        return (False, f"critical_file: {path.name}")

                return (True, "allowed")

            except ValueError:
                continue

        return (False, "outside_workspace")

    def check_operation(
        self,
        path: Path,
        operation: PathPermission,
    ) -> tuple[bool, str]:
        """
        Check if filesystem operation is allowed.

        Args:
            path: Target path
            operation: Operation type

        Returns:
            Tuple of (allowed, reason)
        """
        allowed, reason = self.is_path_allowed(path, operation)

        if not allowed:
            logger.warning(f"Blocked {operation.value} on {path}: {reason}")

        return (allowed, reason)

    def get_safe_path(self, path_str: str) -> Path | None:
        """
        Get safe resolved path if allowed.

        Args:
            path_str: Path string

        Returns:
            Resolved path if allowed, None otherwise
        """
        try:
            path = Path(path_str).resolve()

            allowed, _ = self.is_path_allowed(path, PathPermission.READ)

            if allowed:
                return path

        except Exception as e:
            logger.warning(f"Invalid path: {path_str}: {e}")

        return None

    def list_allowed_directories(self) -> list[Path]:
        """
        List all allowed directory roots.

        Returns:
            List of allowed paths
        """
        return self.allowed_paths.copy()

    def add_allowed_path(self, path: Path) -> None:
        """
        Add path to allowed list.

        Args:
            path: Path to allow
        """
        path = path.resolve()

        if path not in self.allowed_paths:
            self.allowed_paths.append(path)
            logger.info(f"Added allowed path: {path}")

    def remove_allowed_path(self, path: Path) -> bool:
        """
        Remove path from allowed list.

        Args:
            path: Path to remove

        Returns:
            True if removed
        """
        path = path.resolve()

        # Can't remove workspace root
        if path == self.workspace_root:
            logger.warning("Cannot remove workspace root from allowed paths")
            return False

        if path in self.allowed_paths:
            self.allowed_paths.remove(path)
            logger.info(f"Removed allowed path: {path}")
            return True

        return False

    def block_path(self, path: Path) -> None:
        """
        Add path to blocked list.

        Args:
            path: Path to block
        """
        path = path.resolve()

        if path not in self.blocked_paths:
            self.blocked_paths.append(path)
            logger.info(f"Blocked path: {path}")


def check_path_access(
    path: Path,
    permission: PathPermission = PathPermission.READ,
    workspace_root: Path | None = None,
) -> tuple[bool, str]:
    """
    Check if path access is allowed.

    Args:
        path: Path to check
        permission: Required permission
        workspace_root: Workspace root (uses cwd if None)

    Returns:
        Tuple of (allowed, reason)
    """
    if workspace_root is None:
        workspace_root = Path.cwd()

    guard = FilesystemGuard(workspace_root)

    return guard.check_operation(path, permission)
