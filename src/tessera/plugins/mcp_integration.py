"""
Model Context Protocol (MCP) server integration.

Allows connecting to MCP servers for tool discovery and execution.
"""

import json
import subprocess
from typing import Any

from ..logging_config import get_logger

logger = get_logger(__name__)


class MCPServer:
    """
    MCP server connection.

    Connects to MCP server process and provides tool discovery/execution.
    """

    def __init__(
        self,
        name: str,
        command: list[str],
        env: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize MCP server connection.

        Args:
            name: Server name
            command: Command to start server
            env: Environment variables
        """
        self.name = name
        self.command = command
        self.env = env or {}
        self.process: subprocess.Popen | None = None
        self.tools: dict[str, dict[str, Any]] = {}

    def start(self) -> bool:
        """
        Start MCP server process.

        Returns:
            True if started successfully
        """
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**subprocess.os.environ, **self.env},
            )

            logger.info(f"Started MCP server: {self.name}")

            # Discover tools
            self._discover_tools()

            return True

        except (OSError, subprocess.SubprocessError):
            logger.exception(f"Failed to start MCP server {self.name}")
            return False

    def stop(self) -> None:
        """Stop MCP server process."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

            logger.info(f"Stopped MCP server: {self.name}")

    def _discover_tools(self) -> None:
        """Discover tools from MCP server."""
        try:
            # Send initialize request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
            }

            if self.process and self.process.stdin:
                self.process.stdin.write(json.dumps(request).encode() + b"\n")
                self.process.stdin.flush()

                # Read response
                if self.process.stdout:
                    response_line = self.process.stdout.readline()
                    response = json.loads(response_line)

                    if "result" in response and "tools" in response["result"]:
                        for tool in response["result"]["tools"]:
                            self.tools[tool["name"]] = tool

                        logger.info(f"Discovered {len(self.tools)} tools from {self.name}")

        except (OSError, ValueError):
            logger.warning(f"Failed to discover tools from {self.name}")

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Call MCP tool.

        Args:
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found in {self.name}")

        try:
            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                },
            }

            if self.process and self.process.stdin and self.process.stdout:
                self.process.stdin.write(json.dumps(request).encode() + b"\n")
                self.process.stdin.flush()

                response_line = self.process.stdout.readline()
                response = json.loads(response_line)

                if "result" in response:
                    return response["result"]

                if "error" in response:
                    raise RuntimeError(f"MCP error: {response['error']}")

        except (OSError, ValueError, RuntimeError):
            logger.exception(f"Failed to call tool {tool_name}")
            raise

        return None


class MCPServerManager:
    """
    Manages multiple MCP server connections.
    """

    def __init__(self) -> None:
        """Initialize MCP server manager."""
        self.servers: dict[str, MCPServer] = {}

        logger.debug("MCPServerManager initialized")

    def register_server(self, server: MCPServer) -> None:
        """
        Register MCP server.

        Args:
            server: MCP server instance
        """
        self.servers[server.name] = server
        logger.info(f"Registered MCP server: {server.name}")

    def start_server(self, name: str) -> bool:
        """
        Start MCP server.

        Args:
            name: Server name

        Returns:
            True if started
        """
        server = self.servers.get(name)

        if server is None:
            logger.warning(f"MCP server not found: {name}")
            return False

        return server.start()

    def stop_server(self, name: str) -> None:
        """
        Stop MCP server.

        Args:
            name: Server name
        """
        server = self.servers.get(name)

        if server:
            server.stop()

    def stop_all(self) -> None:
        """Stop all MCP servers."""
        for server in self.servers.values():
            server.stop()

        logger.info("Stopped all MCP servers")

    def get_all_tools(self) -> dict[str, dict[str, Any]]:
        """
        Get all tools from all servers.

        Returns:
            Dict of tool_name -> tool_definition
        """
        all_tools = {}

        for server in self.servers.values():
            for tool_name, tool_def in server.tools.items():
                # Prefix with server name to avoid collisions
                prefixed_name = f"{server.name}.{tool_name}"
                all_tools[prefixed_name] = {
                    **tool_def,
                    "server": server.name,
                }

        return all_tools


# Global MCP server manager
_mcp_manager: MCPServerManager | None = None


def get_mcp_manager() -> MCPServerManager:
    """
    Get global MCP server manager.

    Returns:
        Global MCPServerManager
    """
    global _mcp_manager

    if _mcp_manager is None:
        _mcp_manager = MCPServerManager()

    return _mcp_manager
