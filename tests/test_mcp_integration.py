"""Tests for MCP (Model Context Protocol) server integration."""

import json
import subprocess
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from tessera.plugins.mcp_integration import (
    MCPServer,
    MCPServerManager,
    get_mcp_manager,
)


class TestMCPServer:
    """Test MCP server connection."""

    def test_initialization(self) -> None:
        """Test MCP server initialization."""
        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
            env={"VAR": "value"},
        )

        assert server.name == "test-server"
        assert server.command == ["python", "-m", "mcp_server"]
        assert server.env == {"VAR": "value"}
        assert server.process is None
        assert server.tools == {}

    def test_initialization_no_env(self) -> None:
        """Test MCP server initialization without env."""
        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        assert server.env == {}

    @patch("tessera.plugins.mcp_integration.subprocess.Popen")
    @patch("tessera.plugins.mcp_integration.os.environ", {"PATH": "/usr/bin"})
    def test_start_success(self, mock_popen: Mock) -> None:
        """Test successful MCP server start."""
        # Mock process
        mock_process = MagicMock()
        mock_process.stdin = BytesIO()
        mock_process.stdout = BytesIO(
            b'{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"test_tool","description":"Test"}]}}\n'
        )
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        result = server.start()

        assert result is True
        assert server.process == mock_process
        mock_popen.assert_called_once()

    @patch("tessera.plugins.mcp_integration.subprocess.Popen")
    def test_start_failure(self, mock_popen: Mock) -> None:
        """Test failed MCP server start."""
        mock_popen.side_effect = OSError("Command not found")

        server = MCPServer(
            name="test-server",
            command=["nonexistent_command"],
        )

        result = server.start()

        assert result is False
        assert server.process is None

    @patch("tessera.plugins.mcp_integration.subprocess.Popen")
    def test_start_subprocess_error(self, mock_popen: Mock) -> None:
        """Test MCP server start with subprocess error."""
        mock_popen.side_effect = subprocess.SubprocessError("Spawn failed")

        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        result = server.start()

        assert result is False

    def test_stop_no_process(self) -> None:
        """Test stop with no running process."""
        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        # Should not raise
        server.stop()

    def test_stop_graceful(self) -> None:
        """Test graceful process stop."""
        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        mock_process = MagicMock()
        server.process = mock_process

        server.stop()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)

    def test_stop_force_kill(self) -> None:
        """Test force kill when terminate times out."""
        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        mock_process = MagicMock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired("cmd", 5)
        server.process = mock_process

        server.stop()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @patch("tessera.plugins.mcp_integration.subprocess.Popen")
    def test_discover_tools_success(self, mock_popen: Mock) -> None:
        """Test successful tool discovery."""
        tools_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {"name": "tool1", "description": "First tool"},
                    {"name": "tool2", "description": "Second tool"},
                ]
            },
        }

        mock_process = MagicMock()
        mock_process.stdin = BytesIO()
        mock_process.stdout = BytesIO(json.dumps(tools_response).encode() + b"\n")
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        server.start()

        assert len(server.tools) == 2
        assert "tool1" in server.tools
        assert "tool2" in server.tools

    @patch("tessera.plugins.mcp_integration.subprocess.Popen")
    def test_discover_tools_no_result(self, mock_popen: Mock) -> None:
        """Test tool discovery with no result."""
        response = {"jsonrpc": "2.0", "id": 1, "error": "Failed"}

        mock_process = MagicMock()
        mock_process.stdin = BytesIO()
        mock_process.stdout = BytesIO(json.dumps(response).encode() + b"\n")
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        server.start()

        assert len(server.tools) == 0

    @patch("tessera.plugins.mcp_integration.subprocess.Popen")
    def test_discover_tools_invalid_json(self, mock_popen: Mock) -> None:
        """Test tool discovery with invalid JSON."""
        mock_process = MagicMock()
        mock_process.stdin = BytesIO()
        mock_process.stdout = BytesIO(b"invalid json\n")
        mock_popen.return_value = mock_process

        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        # Should not raise
        server.start()
        assert len(server.tools) == 0

    def test_call_tool_not_found(self) -> None:
        """Test calling non-existent tool."""
        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        with pytest.raises(ValueError, match="Tool nonexistent not found"):
            server.call_tool("nonexistent", {})

    def test_call_tool_success(self) -> None:
        """Test successful tool call."""
        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        server.tools = {"test_tool": {"name": "test_tool"}}

        mock_process = MagicMock()
        mock_stdin = BytesIO()
        mock_stdout = BytesIO(json.dumps({"jsonrpc": "2.0", "id": 2, "result": {"output": "success"}}).encode() + b"\n")
        mock_process.stdin = mock_stdin
        mock_process.stdout = mock_stdout
        server.process = mock_process

        result = server.call_tool("test_tool", {"arg": "value"})

        assert result == {"output": "success"}

    def test_call_tool_error_response(self) -> None:
        """Test tool call with error response."""
        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        server.tools = {"test_tool": {"name": "test_tool"}}

        mock_process = MagicMock()
        mock_stdin = BytesIO()
        mock_stdout = BytesIO(
            json.dumps({"jsonrpc": "2.0", "id": 2, "error": {"message": "Tool failed"}}).encode() + b"\n"
        )
        mock_process.stdin = mock_stdin
        mock_process.stdout = mock_stdout
        server.process = mock_process

        with pytest.raises(RuntimeError, match="MCP error"):
            server.call_tool("test_tool", {"arg": "value"})

    def test_call_tool_no_process(self) -> None:
        """Test tool call with no running process."""
        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        server.tools = {"test_tool": {"name": "test_tool"}}

        result = server.call_tool("test_tool", {})

        assert result is None

    def test_call_tool_invalid_json(self) -> None:
        """Test tool call with invalid JSON response."""
        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        server.tools = {"test_tool": {"name": "test_tool"}}

        mock_process = MagicMock()
        mock_stdin = BytesIO()
        mock_stdout = BytesIO(b"invalid json\n")
        mock_process.stdin = mock_stdin
        mock_process.stdout = mock_stdout
        server.process = mock_process

        with pytest.raises(ValueError):
            server.call_tool("test_tool", {})


class TestMCPServerManager:
    """Test MCP server manager."""

    def test_initialization(self) -> None:
        """Test manager initialization."""
        manager = MCPServerManager()

        assert manager.servers == {}

    def test_register_server(self) -> None:
        """Test server registration."""
        manager = MCPServerManager()

        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        manager.register_server(server)

        assert "test-server" in manager.servers
        assert manager.servers["test-server"] == server

    @patch("tessera.plugins.mcp_integration.subprocess.Popen")
    def test_start_server_success(self, mock_popen: Mock) -> None:
        """Test successful server start."""
        mock_process = MagicMock()
        mock_process.stdin = BytesIO()
        mock_process.stdout = BytesIO(b'{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}\n')
        mock_popen.return_value = mock_process

        manager = MCPServerManager()

        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        manager.register_server(server)

        result = manager.start_server("test-server")

        assert result is True

    def test_start_server_not_found(self) -> None:
        """Test starting non-existent server."""
        manager = MCPServerManager()

        result = manager.start_server("nonexistent")

        assert result is False

    def test_stop_server(self) -> None:
        """Test stopping server."""
        manager = MCPServerManager()

        server = MCPServer(
            name="test-server",
            command=["python", "-m", "mcp_server"],
        )

        mock_process = MagicMock()
        server.process = mock_process

        manager.register_server(server)
        manager.stop_server("test-server")

        mock_process.terminate.assert_called_once()

    def test_stop_server_not_found(self) -> None:
        """Test stopping non-existent server."""
        manager = MCPServerManager()

        # Should not raise
        manager.stop_server("nonexistent")

    def test_stop_all(self) -> None:
        """Test stopping all servers."""
        manager = MCPServerManager()

        server1 = MCPServer(name="server1", command=["cmd1"])
        server2 = MCPServer(name="server2", command=["cmd2"])

        mock_process1 = MagicMock()
        mock_process2 = MagicMock()

        server1.process = mock_process1
        server2.process = mock_process2

        manager.register_server(server1)
        manager.register_server(server2)

        manager.stop_all()

        mock_process1.terminate.assert_called_once()
        mock_process2.terminate.assert_called_once()

    def test_get_all_tools_empty(self) -> None:
        """Test getting tools with no servers."""
        manager = MCPServerManager()

        tools = manager.get_all_tools()

        assert tools == {}

    def test_get_all_tools(self) -> None:
        """Test getting all tools from multiple servers."""
        manager = MCPServerManager()

        server1 = MCPServer(name="server1", command=["cmd1"])
        server1.tools = {
            "tool1": {"name": "tool1", "description": "Tool 1"},
            "tool2": {"name": "tool2", "description": "Tool 2"},
        }

        server2 = MCPServer(name="server2", command=["cmd2"])
        server2.tools = {
            "tool3": {"name": "tool3", "description": "Tool 3"},
        }

        manager.register_server(server1)
        manager.register_server(server2)

        tools = manager.get_all_tools()

        assert len(tools) == 3
        assert "server1.tool1" in tools
        assert "server1.tool2" in tools
        assert "server2.tool3" in tools

        assert tools["server1.tool1"]["server"] == "server1"
        assert tools["server2.tool3"]["server"] == "server2"

    def test_get_all_tools_prefixes_names(self) -> None:
        """Test that tool names are prefixed with server name."""
        manager = MCPServerManager()

        server = MCPServer(name="myserver", command=["cmd"])
        server.tools = {"mytool": {"name": "mytool"}}

        manager.register_server(server)

        tools = manager.get_all_tools()

        assert "myserver.mytool" in tools
        assert "mytool" not in tools


class TestGlobalManager:
    """Test global MCP manager."""

    def test_get_mcp_manager_singleton(self) -> None:
        """Test that get_mcp_manager returns singleton."""
        manager1 = get_mcp_manager()
        manager2 = get_mcp_manager()

        assert manager1 is manager2

    def test_get_mcp_manager_creates_instance(self) -> None:
        """Test that get_mcp_manager creates instance."""
        # Clear global
        import tessera.plugins.mcp_integration

        tessera.plugins.mcp_integration._mcp_manager = None

        manager = get_mcp_manager()

        assert isinstance(manager, MCPServerManager)
