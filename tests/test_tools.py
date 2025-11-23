"""Tests for tool system."""

from pathlib import Path

import pytest

from tessera.tools.access_control import RiskLevel, ToolAccessControl
from tessera.tools.discovery import ToolDefinition, ToolRegistry
from tessera.tools.execution import ToolExecutor


@pytest.mark.unit
class TestToolAccessControl:
    """Test tool access control."""

    def test_initialization(self):
        """Test access control initialization."""
        ac = ToolAccessControl(max_risk_level=RiskLevel.MEDIUM)

        assert ac.max_risk_level == RiskLevel.MEDIUM

    def test_check_permission_allowed(self):
        """Test permission check for allowed tool."""
        ac = ToolAccessControl(max_risk_level=RiskLevel.HIGH)

        allowed, reason = ac.check_permission("test_tool", RiskLevel.MEDIUM)

        assert allowed is True
        assert reason == "permitted"

    def test_check_permission_denied(self):
        """Test permission check for denied tool."""
        ac = ToolAccessControl(max_risk_level=RiskLevel.LOW)

        allowed, reason = ac.check_permission("dangerous_tool", RiskLevel.HIGH)

        assert allowed is False
        assert "exceeds max" in reason

    def test_set_tool_risk_override(self):
        """Test overriding tool risk level."""
        ac = ToolAccessControl(max_risk_level=RiskLevel.LOW)

        # Override high-risk tool to low
        ac.set_tool_risk("safe_tool", RiskLevel.SAFE)

        # Should be allowed now
        allowed, _ = ac.check_permission("safe_tool", RiskLevel.HIGH)
        assert allowed is True

    def test_agent_permissions(self):
        """Test per-agent permissions."""
        ac = ToolAccessControl()

        ac.grant_agent_permission("agent1", "tool1")
        ac.grant_agent_permission("agent1", "tool2")

        # Agent without specific permission
        allowed, _ = ac.check_permission("tool1", RiskLevel.LOW, agent_name="agent2")
        assert allowed is True  # Global permission still applies

    def test_requires_approval(self):
        """Test approval requirement check."""
        ac = ToolAccessControl(
            max_risk_level=RiskLevel.HIGH,
            require_approval_above=RiskLevel.MEDIUM,
        )

        assert ac.requires_approval("tool", RiskLevel.HIGH) is True
        assert ac.requires_approval("tool", RiskLevel.LOW) is False


@pytest.mark.unit
class TestToolRegistry:
    """Test tool registry."""

    def test_registry_initialization(self):
        """Test registry initializes with built-in tools."""
        registry = ToolRegistry()

        # Should have built-in tools
        assert "read_file" in registry.tools
        assert "write_file" in registry.tools
        assert "list_directory" in registry.tools
        assert "run_command" in registry.tools

    def test_register_tool(self):
        """Test registering custom tool."""
        registry = ToolRegistry()

        tool = ToolDefinition(
            name="custom_tool",
            description="Custom tool",
            risk_level=RiskLevel.MEDIUM,
            parameters={"arg1": "string"},
            execute=lambda **kwargs: "result",
            source="custom",
        )

        registry.register(tool)

        assert "custom_tool" in registry.tools

    def test_get_tool(self):
        """Test getting tool by name."""
        registry = ToolRegistry()

        tool = registry.get_tool("read_file")

        assert tool is not None
        assert tool.name == "read_file"
        assert tool.risk_level == RiskLevel.SAFE

    def test_list_tools_by_risk(self):
        """Test listing tools filtered by risk level."""
        registry = ToolRegistry()

        safe_tools = registry.list_tools(risk_level=RiskLevel.SAFE)

        assert len(safe_tools) > 0
        assert all(t.risk_level == RiskLevel.SAFE for t in safe_tools)

    def test_unregister_tool(self):
        """Test unregistering tool."""
        registry = ToolRegistry()

        success = registry.unregister("read_file")

        assert success is True
        assert "read_file" not in registry.tools


@pytest.mark.unit
class TestToolExecutor:
    """Test tool execution."""

    def test_executor_initialization(self):
        """Test tool executor initialization."""
        executor = ToolExecutor(agent_name="test-agent", task_id="task-123")

        assert executor.agent_name == "test-agent"
        assert executor.task_id == "task-123"

    def test_execute_safe_tool(self):
        """Test executing safe tool."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = f.name

        try:
            executor = ToolExecutor()
            result = executor.execute("read_file", file_path=temp_path)

            assert "test content" in result

        finally:
            Path(temp_path).unlink()

    def test_execute_nonexistent_tool(self):
        """Test executing non-existent tool."""
        executor = ToolExecutor()

        with pytest.raises(ValueError, match="Tool not found"):
            executor.execute("nonexistent_tool")
