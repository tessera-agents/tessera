"""
Tool discovery and registration.

Discovers tools from plugins and MCP servers.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..logging_config import get_logger
from .access_control import RiskLevel

logger = get_logger(__name__)

# MCP tool name format constant
_MCP_TOOL_NAME_PARTS = 2  # Expected format: "server.tool"


@dataclass
class ToolDefinition:
    """Tool definition with metadata."""

    name: str
    description: str
    risk_level: RiskLevel
    parameters: dict[str, Any]
    execute: Callable[..., Any]
    source: str  # "builtin", "plugin", "mcp"


class ToolRegistry:
    """
    Registry of available tools.

    Manages tool discovery, registration, and lookup.
    """

    def __init__(self) -> None:
        """Initialize tool registry."""
        self.tools: dict[str, ToolDefinition] = {}

        logger.debug("ToolRegistry initialized")

        # Register built-in tools
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in tools."""
        # Filesystem tools
        self.register(
            ToolDefinition(
                name="read_file",
                description="Read file contents",
                risk_level=RiskLevel.SAFE,
                parameters={"file_path": "string"},
                execute=self._read_file,
                source="builtin",
            )
        )

        self.register(
            ToolDefinition(
                name="write_file",
                description="Write content to file",
                risk_level=RiskLevel.LOW,
                parameters={"file_path": "string", "content": "string"},
                execute=self._write_file,
                source="builtin",
            )
        )

        self.register(
            ToolDefinition(
                name="list_directory",
                description="List directory contents",
                risk_level=RiskLevel.SAFE,
                parameters={"path": "string"},
                execute=self._list_directory,
                source="builtin",
            )
        )

        # Command execution
        self.register(
            ToolDefinition(
                name="run_command",
                description="Execute shell command",
                risk_level=RiskLevel.HIGH,
                parameters={"command": "string", "cwd": "string"},
                execute=self._run_command,
                source="builtin",
            )
        )

        logger.debug("Registered built-in tools")

    def register(self, tool: ToolDefinition) -> None:
        """
        Register a tool.

        Args:
            tool: Tool definition
        """
        if tool.name in self.tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")

        self.tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name} (risk: {tool.risk_level.value})")

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Tool name

        Returns:
            True if unregistered
        """
        if name in self.tools:
            del self.tools[name]
            logger.debug(f"Unregistered tool: {name}")
            return True

        return False

    def get_tool(self, name: str) -> ToolDefinition | None:
        """
        Get tool by name.

        Args:
            name: Tool name

        Returns:
            ToolDefinition or None
        """
        return self.tools.get(name)

    def list_tools(self, risk_level: RiskLevel | None = None) -> list[ToolDefinition]:
        """
        List all tools.

        Args:
            risk_level: Optional risk level filter

        Returns:
            List of tools
        """
        tools = list(self.tools.values())

        if risk_level:
            tools = [t for t in tools if t.risk_level == risk_level]

        return tools

    def discover_from_plugins(self) -> int:
        """
        Discover tools from loaded plugins.

        Returns:
            Number of tools discovered
        """
        from ..plugins import get_plugin_manager
        from ..plugins.manager import PluginType

        manager = get_plugin_manager()
        tool_plugins = manager.list_plugins(plugin_type=PluginType.TOOL)

        discovered = 0

        for plugin in tool_plugins:
            if not plugin.enabled:
                continue

            try:
                # Call plugin entry point to get tool definitions
                tools = plugin.entry_point()

                if isinstance(tools, list):
                    for tool in tools:
                        if isinstance(tool, ToolDefinition):
                            self.register(tool)
                            discovered += 1

            except RuntimeError:
                logger.exception(f"Failed to discover tools from plugin {plugin.name}")

        logger.info(f"Discovered {discovered} tools from plugins")

        return discovered

    def discover_from_mcp(self) -> int:
        """
        Discover tools from MCP servers.

        Returns:
            Number of tools discovered
        """
        from ..plugins.mcp_integration import get_mcp_manager

        mcp_manager = get_mcp_manager()
        all_tools = mcp_manager.get_all_tools()

        for tool_name, tool_def in all_tools.items():
            # Create tool definition from MCP tool
            # Use default argument to bind tool_name in lambda
            mcp_tool = ToolDefinition(
                name=tool_name,
                description=tool_def.get("description", ""),
                risk_level=RiskLevel.MEDIUM,  # Default for MCP tools
                parameters=tool_def.get("parameters", {}),
                execute=lambda tool_name=tool_name, **kwargs: self._execute_mcp_tool(tool_name, kwargs),
                source="mcp",
            )

            self.register(mcp_tool)

        logger.info(f"Discovered {len(all_tools)} tools from MCP servers")

        return len(all_tools)

    # Built-in tool implementations
    def _read_file(self, file_path: str) -> str:
        """Read file implementation."""
        from pathlib import Path

        return Path(file_path).read_text()

    def _write_file(self, file_path: str, content: str) -> bool:
        """Write file implementation."""
        from pathlib import Path

        Path(file_path).write_text(content)
        return True

    def _list_directory(self, path: str) -> list[str]:
        """List directory implementation."""
        from pathlib import Path

        return [str(p) for p in Path(path).iterdir()]

    def _run_command(self, command: str, cwd: str = ".") -> dict[str, Any]:
        """Run command implementation."""
        import shlex
        import subprocess

        # Split command safely
        cmd_parts = shlex.split(command)

        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def _execute_mcp_tool(self, tool_name: str, kwargs: dict[str, Any]) -> Any:
        """Execute MCP tool."""
        from ..plugins.mcp_integration import get_mcp_manager

        # Parse server name from tool_name (format: server.tool)
        parts = tool_name.split(".", 1)
        if len(parts) != _MCP_TOOL_NAME_PARTS:
            raise ValueError(f"Invalid MCP tool name: {tool_name}")

        server_name, actual_tool_name = parts

        mcp_manager = get_mcp_manager()
        server = mcp_manager.servers.get(server_name)

        if server is None:
            raise ValueError(f"MCP server not found: {server_name}")

        return server.call_tool(actual_tool_name, kwargs)


# Global tool registry
_tool_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """
    Get global tool registry.

    Returns:
        Global ToolRegistry
    """
    global _tool_registry

    if _tool_registry is None:
        _tool_registry = ToolRegistry()

    return _tool_registry


def register_tool(tool: ToolDefinition) -> None:
    """
    Register a tool.

    Args:
        tool: Tool definition
    """
    registry = get_tool_registry()
    registry.register(tool)


def discover_tools() -> int:
    """
    Discover all tools from plugins and MCP.

    Returns:
        Total tools discovered
    """
    registry = get_tool_registry()

    plugin_count = registry.discover_from_plugins()
    mcp_count = registry.discover_from_mcp()

    total = plugin_count + mcp_count

    logger.info(f"Discovered {total} tools ({plugin_count} plugins, {mcp_count} MCP)")

    return total


def check_tool_permission(
    tool_name: str,
    agent_name: str | None = None,
) -> tuple[bool, str]:
    """
    Check if agent has permission to use tool.

    Args:
        tool_name: Tool name
        agent_name: Agent name

    Returns:
        Tuple of (allowed, reason)
    """
    from .access_control import get_access_control

    registry = get_tool_registry()
    tool = registry.get_tool(tool_name)

    if tool is None:
        return (False, "tool_not_found")

    access_control = get_access_control()

    return access_control.check_permission(tool_name, tool.risk_level, agent_name)
