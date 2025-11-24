"""
Action logging for tracking agent operations.

Records all actions performed by agents: commands run, files created/modified/deleted.
"""

import json
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from tessera.config.xdg import get_tessera_cache_dir
from tessera.logging_config import get_logger

logger = get_logger(__name__)


class ActionType(Enum):
    """Types of actions that can be logged."""

    COMMAND_RUN = "command_run"
    FILE_CREATE = "file_create"
    FILE_MODIFY = "file_modify"
    FILE_DELETE = "file_delete"
    FILE_READ = "file_read"
    NETWORK_REQUEST = "network_request"
    AGENT_DECISION = "agent_decision"


class ActionLogger:
    """
    Logs all actions performed during execution.

    Actions are stored as JSONL for easy parsing and analysis.
    """

    def __init__(self, log_file: Path | None = None) -> None:
        """
        Initialize action logger.

        Args:
            log_file: Path to log file (defaults to XDG cache)
        """
        if log_file is None:
            cache_dir = get_tessera_cache_dir()
            log_file = cache_dir / "actions.jsonl"

        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(f"ActionLogger initialized: {self.log_file}")

    def log_action(
        self,
        action_type: ActionType,
        description: str,
        agent_name: str | None = None,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Log an action.

        Args:
            action_type: Type of action
            description: Human-readable description
            agent_name: Agent performing the action
            task_id: Related task ID
            metadata: Additional action metadata
        """
        action_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action_type": action_type.value,
            "description": description,
            "agent_name": agent_name,
            "task_id": task_id,
            "metadata": metadata or {},
        }

        try:
            with Path(self.log_file).open("a") as f:
                f.write(json.dumps(action_record) + "\n")

            logger.debug(f"Logged {action_type.value}: {description}")

        except OSError as e:
            logger.warning(f"Failed to log action: {e}")

    def log_command(
        self,
        command: str,
        exit_code: int,
        agent_name: str | None = None,
        task_id: str | None = None,
        output: str | None = None,
    ) -> None:
        """
        Log command execution.

        Args:
            command: Command that was run
            exit_code: Exit code
            agent_name: Agent that ran command
            task_id: Related task
            output: Command output (truncated)
        """
        self.log_action(
            ActionType.COMMAND_RUN,
            f"Ran: {command}",
            agent_name=agent_name,
            task_id=task_id,
            metadata={
                "command": command,
                "exit_code": exit_code,
                "output_preview": output[:500] if output else None,
            },
        )

    def log_file_operation(
        self,
        operation: ActionType,
        file_path: str | Path,
        agent_name: str | None = None,
        task_id: str | None = None,
    ) -> None:
        """
        Log file operation.

        Args:
            operation: Type of file operation
            file_path: Path to file
            agent_name: Agent performing operation
            task_id: Related task
        """
        self.log_action(
            operation,
            f"{operation.value}: {file_path}",
            agent_name=agent_name,
            task_id=task_id,
            metadata={"file_path": str(file_path)},
        )

    def log_network_request(
        self,
        url: str,
        method: str = "GET",
        status_code: int | None = None,
        agent_name: str | None = None,
        task_id: str | None = None,
    ) -> None:
        """
        Log network request.

        Args:
            url: Request URL
            method: HTTP method
            status_code: Response status code
            agent_name: Agent making request
            task_id: Related task
        """
        self.log_action(
            ActionType.NETWORK_REQUEST,
            f"{method} {url}",
            agent_name=agent_name,
            task_id=task_id,
            metadata={"url": url, "method": method, "status_code": status_code},
        )

    def get_actions_for_task(self, task_id: str) -> list[dict[str, Any]]:
        """
        Get all actions for a specific task.

        Args:
            task_id: Task identifier

        Returns:
            List of action records
        """
        actions = []

        try:
            if not self.log_file.exists():
                return []

            with Path(self.log_file).open() as f:
                for line in f:
                    try:
                        action = json.loads(line)
                        if action.get("task_id") == task_id:
                            actions.append(action)
                    except json.JSONDecodeError:
                        continue

        except OSError as e:
            logger.warning(f"Failed to read actions: {e}")

        return actions

    def get_actions_for_agent(self, agent_name: str) -> list[dict[str, Any]]:
        """
        Get all actions for a specific agent.

        Args:
            agent_name: Agent name

        Returns:
            List of action records
        """
        actions = []

        try:
            if not self.log_file.exists():
                return []

            with Path(self.log_file).open() as f:
                for line in f:
                    try:
                        action = json.loads(line)
                        if action.get("agent_name") == agent_name:
                            actions.append(action)
                    except json.JSONDecodeError:
                        continue

        except OSError as e:
            logger.warning(f"Failed to read actions: {e}")

        return actions


# Global action logger instance
_action_logger: ActionLogger | None = None


def get_action_logger() -> ActionLogger:
    """
    Get global action logger instance.

    Returns:
        Global ActionLogger
    """
    global _action_logger

    if _action_logger is None:
        _action_logger = ActionLogger()

    return _action_logger
