"""
Tessera workspace management.

Manages project workspaces with sandboxing and permissions.
"""

from .filesystem_protection import FilesystemGuard, PathPermission, check_path_access
from .manager import Workspace, WorkspaceManager, get_workspace_manager
from .sandbox import Sandbox, SandboxConfig, create_sandbox

__all__ = [
    "FilesystemGuard",
    "PathPermission",
    "Sandbox",
    "SandboxConfig",
    "Workspace",
    "WorkspaceManager",
    "check_path_access",
    "create_sandbox",
    "get_workspace_manager",
]
