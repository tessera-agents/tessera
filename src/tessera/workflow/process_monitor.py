"""
Process monitoring to track and manage spawned subprocesses.

Prevents runaway processes and ensures cleanup.
"""

import atexit
from typing import Any

import psutil

from ..logging_config import get_logger

logger = get_logger(__name__)


class ProcessMonitor:
    """
    Monitors and manages spawned subprocesses.

    Tracks all processes created during execution and ensures proper cleanup.
    """

    def __init__(self) -> None:
        """Initialize process monitor."""
        self.tracked_processes: dict[int, dict[str, Any]] = {}  # PID -> process info
        self.parent_pid = psutil.Process().pid

        # Register cleanup on exit
        atexit.register(self.cleanup_all)

        logger.debug(f"ProcessMonitor initialized for PID {self.parent_pid}")

    def register_process(
        self,
        process: psutil.Process | Any,
        name: str,
        task_id: str | None = None,
        agent_name: str | None = None,
    ) -> None:
        """
        Register a spawned process for tracking.

        Args:
            process: Process object (psutil.Process or subprocess.Popen)
            name: Process name/description
            task_id: Related task ID
            agent_name: Agent that spawned process
        """
        pid = process.pid if hasattr(process, "pid") else None

        if pid:
            self.tracked_processes[pid] = {
                "name": name,
                "task_id": task_id,
                "agent_name": agent_name,
                "process": process,
            }

            logger.debug(f"Registered process {pid}: {name}")

    def unregister_process(self, pid: int) -> None:
        """
        Unregister a process after it completes.

        Args:
            pid: Process ID
        """
        if pid in self.tracked_processes:
            del self.tracked_processes[pid]
            logger.debug(f"Unregistered process {pid}")

    def check_for_runaways(self) -> list[dict[str, Any]]:
        """
        Check for runaway processes.

        Returns:
            List of processes that may be runaway
        """
        runaways = []

        for pid, info in list(self.tracked_processes.items()):
            try:
                process = psutil.Process(pid)

                # Check if process is still running
                if not process.is_running():
                    self.unregister_process(pid)
                    continue

                # Check CPU usage (>90% for >60s might indicate runaway)
                cpu_percent = process.cpu_percent(interval=0.1)

                # Check memory (>1GB might indicate leak)
                memory_mb = process.memory_info().rss / (1024 * 1024)

                if cpu_percent > 90 or memory_mb > 1024:
                    runaways.append(
                        {
                            "pid": pid,
                            "name": info["name"],
                            "cpu_percent": cpu_percent,
                            "memory_mb": memory_mb,
                            "task_id": info.get("task_id"),
                        }
                    )

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process terminated or no access
                self.unregister_process(pid)

        return runaways

    def get_process_count(self) -> int:
        """
        Get count of tracked processes.

        Returns:
            Number of tracked processes
        """
        # Clean up terminated processes first
        for pid in list(self.tracked_processes.keys()):
            try:
                process = psutil.Process(pid)
                if not process.is_running():
                    self.unregister_process(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.unregister_process(pid)

        return len(self.tracked_processes)

    def kill_process(self, pid: int, force: bool = False) -> bool:
        """
        Terminate a tracked process.

        Args:
            pid: Process ID
            force: Use SIGKILL instead of SIGTERM

        Returns:
            True if process terminated
        """
        try:
            process = psutil.Process(pid)

            if force:
                process.kill()  # SIGKILL
            else:
                process.terminate()  # SIGTERM

            # Wait for termination
            process.wait(timeout=5)

            self.unregister_process(pid)

            logger.info(f"Terminated process {pid}")
            return True

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
            logger.warning(f"Failed to terminate process {pid}: {e}")
            return False

    def cleanup_all(self) -> None:
        """Clean up all tracked processes on shutdown."""
        if not self.tracked_processes:
            return

        logger.info(f"Cleaning up {len(self.tracked_processes)} tracked processes")

        for pid in list(self.tracked_processes.keys()):
            try:
                self.kill_process(pid, force=False)
            except Exception as e:
                logger.warning(f"Error cleaning up process {pid}: {e}")

    def get_status_summary(self) -> dict[str, Any]:
        """
        Get summary of tracked processes.

        Returns:
            Dict with process statistics
        """
        self.check_for_runaways()  # Clean up terminated

        return {
            "total_tracked": len(self.tracked_processes),
            "processes": [
                {
                    "pid": pid,
                    "name": info["name"],
                    "task_id": info.get("task_id"),
                    "agent_name": info.get("agent_name"),
                }
                for pid, info in self.tracked_processes.items()
            ],
        }


# Global process monitor
_process_monitor: ProcessMonitor | None = None


def get_process_monitor() -> ProcessMonitor:
    """
    Get global process monitor instance.

    Returns:
        Global ProcessMonitor
    """
    global _process_monitor

    if _process_monitor is None:
        _process_monitor = ProcessMonitor()

    return _process_monitor
