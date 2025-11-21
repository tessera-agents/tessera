"""
Agent identity management for Slack.

Generates identities from agent configuration, no hard-coded defaults.
"""

from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class AgentIdentity:
    """Identity configuration for an agent in Slack."""

    name: str
    display_name: str  # "Tessera: Python Expert"
    emoji: str  # ":snake:"
    color: str  # "#4ECDC4"
    description: str  # "Python coding specialist"


class AgentIdentityManager:
    """
    Manages agent identities for Slack.

    Identities are generated from agent configuration - no hard-coded defaults.
    """

    # Emoji suggestions based on keywords (not defaults!)
    EMOJI_HINTS = {
        "supervisor": ":construction_worker:",
        "orchestrator": ":conductor:",
        "python": ":snake:",
        "javascript": ":yellow_square:",
        "test": ":test_tube:",
        "review": ":mag:",
        "security": ":shield:",
        "documentation": ":memo:",
        "writer": ":pencil:",
        "devops": ":gear:",
        "architect": ":triangular_ruler:",
        "researcher": ":books:",
        "data": ":bar_chart:",
    }

    # Color palette (cycled through agents)
    COLORS = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#5F27CD",
        "#EE5A6F", "#00D2D3", "#FF9FF3", "#54A0FF",
        "#FFA502", "#2ED573", "#FF6348", "#1E90FF",
    ]

    def __init__(self, agent_configs: Optional[List] = None):
        """
        Initialize from agent configurations.

        Args:
            agent_configs: List of AgentDefinition from TesseraSettings
        """
        self.identities: Dict[str, AgentIdentity] = {}
        self._color_index = 0

        if agent_configs:
            for config in agent_configs:
                self.register_from_config(config)

    def register_from_config(self, agent_config) -> None:
        """
        Create identity from agent configuration.

        Args:
            agent_config: AgentDefinition from config
        """
        # Get emoji based on name/capabilities
        emoji = self._suggest_emoji(agent_config)

        # Assign next color
        color = self.COLORS[self._color_index % len(self.COLORS)]
        self._color_index += 1

        # Get description from system prompt or capabilities
        description = self._extract_description(agent_config)

        identity = AgentIdentity(
            name=agent_config.name,
            display_name=f"Tessera: {agent_config.name.replace('-', ' ').title()}",
            emoji=emoji,
            color=color,
            description=description,
        )

        self.identities[agent_config.name] = identity

    def _suggest_emoji(self, config) -> str:
        """Suggest emoji based on agent name and capabilities."""
        name_lower = config.name.lower()

        # Check name first
        for keyword, emoji in self.EMOJI_HINTS.items():
            if keyword in name_lower:
                return emoji

        # Check role if available
        if hasattr(config, 'role') and config.role:
            role_lower = config.role.lower()
            for keyword, emoji in self.EMOJI_HINTS.items():
                if keyword in role_lower:
                    return emoji

        # Check capabilities
        if hasattr(config, 'capabilities') and config.capabilities:
            for cap in config.capabilities:
                cap_lower = cap.lower()
                for keyword, emoji in self.EMOJI_HINTS.items():
                    if keyword in cap_lower:
                        return emoji

        return ":robot_face:"

    def _extract_description(self, config) -> str:
        """Extract short description from config."""
        # Try system_prompt first
        if hasattr(config, 'system_prompt') and config.system_prompt:
            # Take first line or first 100 chars
            first_line = config.system_prompt.split('\n')[0]
            return first_line[:100].strip()

        # Try capabilities
        if hasattr(config, 'capabilities') and config.capabilities:
            return ", ".join(config.capabilities[:3])

        # Fallback
        return f"Agent: {config.name}"

    def get_identity(self, agent_name: str) -> AgentIdentity:
        """
        Get identity for agent.

        If agent not registered (shouldn't happen in normal use),
        creates a minimal fallback identity.

        Args:
            agent_name: Agent name

        Returns:
            AgentIdentity
        """
        if agent_name in self.identities:
            return self.identities[agent_name]

        # Fallback for unknown agents (shouldn't happen)
        return AgentIdentity(
            name=agent_name,
            display_name=f"Tessera: {agent_name.replace('-', ' ').title()}",
            emoji=":robot_face:",
            color="#95A5A6",
            description=f"Agent: {agent_name}",
        )

    def register_identity(self, identity: AgentIdentity) -> None:
        """
        Manually register an identity.

        Args:
            identity: AgentIdentity to register
        """
        self.identities[identity.name] = identity
