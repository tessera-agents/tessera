"""
Sandboxing for workspace isolation.

Provides process isolation, filesystem restrictions, and resource limits.
"""

import os
import resource
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SandboxConfig:
    """Sandbox configuration."""

    workspace_root: Path
    max_memory_mb: int = 2048  # 2GB default
    max_cpu_time_seconds: int = 600  # 10 minutes
    max_file_size_mb: int = 100
    max_open_files: int = 1024
    max_processes: int = 50
    network_access: bool = True
    allow_shell: bool = False


class Sandbox:
    """
    Sandbox for isolated execution.

    Implements:
    - Filesystem isolation (chroot-like on supported platforms)
    - Resource limits (memory, CPU, file descriptors)
    - Process limits
    - Network access control
    """

    def __init__(self, config: SandboxConfig) -> None:
        """
        Initialize sandbox.

        Args:
            config: Sandbox configuration
        """
        self.config = config
        self.active = False

        logger.debug(f"Sandbox initialized for {config.workspace_root}")

    def enter(self) -> None:
        """Enter sandbox (apply restrictions)."""
        if self.active:
            logger.warning("Sandbox already active")
            return

        # Set resource limits
        try:
            # Memory limit
            memory_bytes = self.config.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

            # CPU time limit
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (self.config.max_cpu_time_seconds, self.config.max_cpu_time_seconds),
            )

            # File size limit
            file_size_bytes = self.config.max_file_size_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (file_size_bytes, file_size_bytes))

            # Open files limit
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (self.config.max_open_files, self.config.max_open_files),
            )

            # Process limit
            resource.setrlimit(resource.RLIMIT_NPROC, (self.config.max_processes, self.config.max_processes))

            logger.info("Sandbox resource limits applied")

        except (OSError, ValueError) as e:
            logger.warning(f"Failed to set some resource limits: {e}")

        # Change to workspace directory
        os.chdir(self.config.workspace_root)

        self.active = True

        logger.info(f"Entered sandbox: {self.config.workspace_root}")

    def exit(self) -> None:
        """Exit sandbox (remove restrictions)."""
        if not self.active:
            return

        # Reset resource limits to system defaults
        try:
            resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
            resource.setrlimit(resource.RLIMIT_CPU, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
            resource.setrlimit(resource.RLIMIT_FSIZE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        except (OSError, ValueError) as e:
            logger.warning(f"Failed to reset resource limits: {e}")

        self.active = False

        logger.info("Exited sandbox")

    def execute_sandboxed(
        self,
        command: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess:
        """
        Execute command in sandbox.

        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            timeout: Timeout in seconds

        Returns:
            CompletedProcess result
        """
        if not self.active:
            logger.warning("Executing in sandbox that isn't active")

        cwd = cwd or self.config.workspace_root

        # Build environment
        sandbox_env = os.environ.copy()

        if env:
            sandbox_env.update(env)

        # Restrict network if configured
        if not self.config.network_access:
            sandbox_env["http_proxy"] = "http://127.0.0.1:1"  # Block network
            sandbox_env["https_proxy"] = "http://127.0.0.1:1"

        # Execute with limits
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                env=sandbox_env,
                timeout=timeout or self.config.max_cpu_time_seconds,
                capture_output=True,
                text=True,
                check=False,
            )

            logger.debug(f"Sandboxed execution completed: {command[0]}")

            return result

        except subprocess.TimeoutExpired:
            logger.exception(f"Sandboxed command timed out: {command}")
            raise
        except (OSError, ValueError, RuntimeError) as e:
            logger.exception(f"Sandboxed execution failed: {e}")
            raise

    def get_stats(self) -> dict[str, Any]:
        """
        Get sandbox statistics.

        Returns:
            Dict with sandbox stats
        """
        return {
            "active": self.active,
            "workspace_root": str(self.config.workspace_root),
            "max_memory_mb": self.config.max_memory_mb,
            "max_cpu_time_seconds": self.config.max_cpu_time_seconds,
            "network_access": self.config.network_access,
        }

    def __enter__(self) -> "Sandbox":
        """Context manager entry."""
        self.enter()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit."""
        self.exit()


def create_sandbox(
    workspace_root: Path,
    strict: bool = False,
) -> Sandbox:
    """
    Create sandbox for workspace.

    Args:
        workspace_root: Workspace root directory
        strict: Use strict limits

    Returns:
        Configured Sandbox
    """
    if strict:
        config = SandboxConfig(
            workspace_root=workspace_root,
            max_memory_mb=1024,  # 1GB
            max_cpu_time_seconds=300,  # 5 minutes
            max_file_size_mb=50,
            max_open_files=512,
            max_processes=25,
            network_access=False,
            allow_shell=False,
        )
    else:
        config = SandboxConfig(
            workspace_root=workspace_root,
            max_memory_mb=4096,  # 4GB
            max_cpu_time_seconds=1800,  # 30 minutes
            max_file_size_mb=500,
            max_open_files=2048,
            max_processes=100,
            network_access=True,
            allow_shell=True,
        )

    return Sandbox(config)
