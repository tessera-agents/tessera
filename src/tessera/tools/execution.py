"""
Tool execution with access control and logging.

Wraps tool calls with permission checks and action logging.
"""

from typing import Any

from ..logging_config import get_logger
from ..workflow.action_logger import get_action_logger
from .access_control import check_tool_permission
from .discovery import get_tool_registry

logger = get_logger(__name__)


class ToolExecutor:
    """
    Executes tools with access control.

    Wraps tool execution with:
    - Permission checks
    - Action logging
    - Error handling
    - Approval workflows
    """

    def __init__(self, agent_name: str | None = None, task_id: str | None = None) -> None:
        """
        Initialize tool executor.

        Args:
            agent_name: Agent executing tools
            task_id: Current task ID
        """
        self.agent_name = agent_name
        self.task_id = task_id
        self.action_logger = get_action_logger()
        self.tool_registry = get_tool_registry()

    def execute(self, tool_name: str, **kwargs: Any) -> Any:
        """
        Execute a tool.

        Args:
            tool_name: Tool name
            **kwargs: Tool arguments

        Returns:
            Tool execution result
        """
        # Get tool
        tool = self.tool_registry.get_tool(tool_name)

        if tool is None:
            error = f"Tool not found: {tool_name}"
            logger.error(error)
            raise ValueError(error)

        # Check permission
        allowed, reason = check_tool_permission(tool_name, tool.risk_level, self.agent_name)

        if not allowed:
            error = f"Tool execution denied: {reason}"
            logger.warning(f"Agent {self.agent_name} denied {tool_name}: {reason}")
            raise PermissionError(error)

        # Log action
        from ..workflow.action_logger import ActionType

        self.action_logger.log_action(
            action_type=ActionType.COMMAND_RUN if tool_name == "run_command" else ActionType.AGENT_DECISION,
            description=f"Executing tool: {tool_name}",
            agent_name=self.agent_name,
            task_id=self.task_id,
            metadata={"tool": tool_name, "arguments": kwargs},
        )

        # Execute tool
        try:
            result = tool.execute(**kwargs)

            logger.debug(f"Tool {tool_name} executed successfully")

            return result

        except Exception:
            logger.exception(f"Tool {tool_name} execution failed")
            raise


def execute_tool(
    tool_name: str,
    agent_name: str | None = None,
    task_id: str | None = None,
    **kwargs: Any,
) -> Any:
    """
    Execute a tool with access control.

    Args:
        tool_name: Tool name
        agent_name: Agent name
        task_id: Task ID
        **kwargs: Tool arguments

    Returns:
        Tool execution result
    """
    executor = ToolExecutor(agent_name=agent_name, task_id=task_id)
    return executor.execute(tool_name, **kwargs)
