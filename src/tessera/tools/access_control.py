"""
Risk-based access control for tool execution.

Implements security levels and approval workflows for tools.
"""

from enum import Enum
from typing import Any

from ..logging_config import get_logger

logger = get_logger(__name__)


class RiskLevel(Enum):
    """Tool risk levels."""

    SAFE = "safe"  # Read-only, no side effects
    LOW = "low"  # Write files in project directory
    MEDIUM = "medium"  # Execute commands, network requests
    HIGH = "high"  # System modifications, external APIs with credentials
    CRITICAL = "critical"  # Destructive operations, security implications


class ToolAccessControl:
    """
    Controls tool access based on risk level.

    Implements:
    - Risk-based allowlist/blocklist
    - Per-agent tool permissions
    - Approval workflows for high-risk operations
    """

    def __init__(
        self,
        max_risk_level: RiskLevel = RiskLevel.MEDIUM,
        require_approval_above: RiskLevel | None = None,
    ) -> None:
        """
        Initialize access control.

        Args:
            max_risk_level: Maximum allowed risk level
            require_approval_above: Require approval for tools above this level
        """
        self.max_risk_level = max_risk_level
        self.require_approval_above = require_approval_above
        self.tool_overrides: dict[str, RiskLevel] = {}  # tool_name -> override level
        self.agent_permissions: dict[str, set[str]] = {}  # agent_name -> allowed tools

        logger.debug(f"ToolAccessControl: max_risk={max_risk_level.value}")

    def set_tool_risk(self, tool_name: str, risk_level: RiskLevel) -> None:
        """
        Override risk level for specific tool.

        Args:
            tool_name: Tool name
            risk_level: Risk level override
        """
        self.tool_overrides[tool_name] = risk_level
        logger.debug(f"Set tool risk: {tool_name} -> {risk_level.value}")

    def grant_agent_permission(self, agent_name: str, tool_name: str) -> None:
        """
        Grant agent permission to use specific tool.

        Args:
            agent_name: Agent name
            tool_name: Tool name
        """
        if agent_name not in self.agent_permissions:
            self.agent_permissions[agent_name] = set()

        self.agent_permissions[agent_name].add(tool_name)
        logger.debug(f"Granted {agent_name} permission to use {tool_name}")

    def revoke_agent_permission(self, agent_name: str, tool_name: str) -> None:
        """
        Revoke agent permission to use tool.

        Args:
            agent_name: Agent name
            tool_name: Tool name
        """
        if agent_name in self.agent_permissions:
            self.agent_permissions[agent_name].discard(tool_name)
            logger.debug(f"Revoked {agent_name} permission for {tool_name}")

    def check_permission(
        self,
        tool_name: str,
        tool_risk: RiskLevel,
        agent_name: str | None = None,
    ) -> tuple[bool, str]:
        """
        Check if tool execution is permitted.

        Args:
            tool_name: Tool name
            tool_risk: Tool risk level
            agent_name: Optional agent name

        Returns:
            Tuple of (allowed, reason)
        """
        # Check tool override
        if tool_name in self.tool_overrides:
            tool_risk = self.tool_overrides[tool_name]

        # Check max risk level
        risk_order = list(RiskLevel)

        if risk_order.index(tool_risk) > risk_order.index(self.max_risk_level):
            return (False, f"Tool risk {tool_risk.value} exceeds max {self.max_risk_level.value}")

        # Check agent-specific permissions
        if agent_name and agent_name in self.agent_permissions:
            if tool_name not in self.agent_permissions[agent_name]:
                return (False, f"Agent {agent_name} not authorized for {tool_name}")

        return (True, "permitted")

    def requires_approval(self, tool_name: str, tool_risk: RiskLevel) -> bool:
        """
        Check if tool requires approval.

        Args:
            tool_name: Tool name
            tool_risk: Tool risk level

        Returns:
            True if approval required
        """
        if self.require_approval_above is None:
            return False

        # Check override
        if tool_name in self.tool_overrides:
            tool_risk = self.tool_overrides[tool_name]

        risk_order = list(RiskLevel)

        return risk_order.index(tool_risk) > risk_order.index(self.require_approval_above)

    def get_allowed_tools(self, agent_name: str | None = None) -> list[str]:
        """
        Get list of allowed tools.

        Args:
            agent_name: Optional agent name

        Returns:
            List of allowed tool names
        """
        if agent_name and agent_name in self.agent_permissions:
            return sorted(self.agent_permissions[agent_name])

        # Return all tools up to max risk level
        # This would need tool registry integration
        return []

    def get_stats(self) -> dict[str, Any]:
        """
        Get access control statistics.

        Returns:
            Dict with stats
        """
        return {
            "max_risk_level": self.max_risk_level.value,
            "require_approval_above": self.require_approval_above.value
            if self.require_approval_above
            else None,
            "tool_overrides": len(self.tool_overrides),
            "agent_permissions": len(self.agent_permissions),
        }


# Global access control
_access_control: ToolAccessControl | None = None


def get_access_control() -> ToolAccessControl:
    """
    Get global access control instance.

    Returns:
        Global ToolAccessControl
    """
    global _access_control

    if _access_control is None:
        _access_control = ToolAccessControl()

    return _access_control


def check_tool_permission(
    tool_name: str,
    tool_risk: RiskLevel,
    agent_name: str | None = None,
) -> tuple[bool, str]:
    """
    Check tool execution permission.

    Args:
        tool_name: Tool name
        tool_risk: Tool risk level
        agent_name: Optional agent name

    Returns:
        Tuple of (allowed, reason)
    """
    access_control = get_access_control()
    return access_control.check_permission(tool_name, tool_risk, agent_name)
