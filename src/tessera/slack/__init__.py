"""Enhanced Slack integration."""

from .agent_identity import AgentIdentityManager
from .multi_channel import MultiChannelSlackClient

__all__ = ["AgentIdentityManager", "MultiChannelSlackClient"]
