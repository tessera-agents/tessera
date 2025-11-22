"""
Plugin management for Tessera.

Manages plugin lifecycle, discovery, and execution.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..logging_config import get_logger

logger = get_logger(__name__)


class PluginType(Enum):
    """Plugin types."""

    TOOL = "tool"  # Tool plugins (add new tools)
    AGENT = "agent"  # Agent plugins (custom agent types)
    WORKFLOW = "workflow"  # Workflow plugins (custom phases)
    OBSERVER = "observer"  # Observer plugins (custom metrics/tracing)
    MCP_SERVER = "mcp_server"  # MCP server integration


@dataclass
class Plugin:
    """
    Plugin definition.

    Represents a loaded plugin with metadata and entry point.
    """

    name: str
    plugin_type: PluginType
    version: str
    description: str
    entry_point: Callable[..., Any]
    config: dict[str, Any]
    enabled: bool = True


class PluginManager:
    """
    Manages Tessera plugins.

    Handles plugin loading, registration, and execution.
    """

    def __init__(self) -> None:
        """Initialize plugin manager."""
        self.plugins: dict[str, Plugin] = {}
        self.hooks: dict[str, list[Callable]] = {}

        logger.debug("PluginManager initialized")

    def register_plugin(self, plugin: Plugin) -> None:
        """
        Register a plugin.

        Args:
            plugin: Plugin to register
        """
        if plugin.name in self.plugins:
            logger.warning(f"Plugin {plugin.name} already registered, overwriting")

        self.plugins[plugin.name] = plugin
        logger.info(f"Registered plugin: {plugin.name} ({plugin.plugin_type.value})")

    def unregister_plugin(self, name: str) -> bool:
        """
        Unregister a plugin.

        Args:
            name: Plugin name

        Returns:
            True if unregistered
        """
        if name in self.plugins:
            del self.plugins[name]
            logger.info(f"Unregistered plugin: {name}")
            return True

        return False

    def get_plugin(self, name: str) -> Plugin | None:
        """
        Get plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin or None
        """
        return self.plugins.get(name)

    def list_plugins(self, plugin_type: PluginType | None = None) -> list[Plugin]:
        """
        List all plugins.

        Args:
            plugin_type: Optional type filter

        Returns:
            List of plugins
        """
        plugins = list(self.plugins.values())

        if plugin_type:
            plugins = [p for p in plugins if p.plugin_type == plugin_type]

        return plugins

    def enable_plugin(self, name: str) -> bool:
        """
        Enable a plugin.

        Args:
            name: Plugin name

        Returns:
            True if enabled
        """
        plugin = self.get_plugin(name)

        if plugin is None:
            return False

        plugin.enabled = True
        logger.info(f"Enabled plugin: {name}")

        return True

    def disable_plugin(self, name: str) -> bool:
        """
        Disable a plugin.

        Args:
            name: Plugin name

        Returns:
            True if disabled
        """
        plugin = self.get_plugin(name)

        if plugin is None:
            return False

        plugin.enabled = False
        logger.info(f"Disabled plugin: {name}")

        return True

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """
        Register hook callback.

        Args:
            hook_name: Hook name (e.g., "before_task_execute")
            callback: Callback function
        """
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []

        self.hooks[hook_name].append(callback)
        logger.debug(f"Registered hook: {hook_name}")

    def execute_hooks(self, hook_name: str, *args: Any, **kwargs: Any) -> list[Any]:
        """
        Execute all callbacks for a hook.

        Args:
            hook_name: Hook name
            *args: Hook arguments
            **kwargs: Hook keyword arguments

        Returns:
            List of hook results
        """
        if hook_name not in self.hooks:
            return []

        results = []

        for callback in self.hooks[hook_name]:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook {hook_name} callback failed: {e}")

        return results

    def get_stats(self) -> dict[str, Any]:
        """
        Get plugin statistics.

        Returns:
            Dict with plugin stats
        """
        return {
            "total_plugins": len(self.plugins),
            "enabled_plugins": sum(1 for p in self.plugins.values() if p.enabled),
            "disabled_plugins": sum(1 for p in self.plugins.values() if not p.enabled),
            "by_type": {
                ptype.value: sum(1 for p in self.plugins.values() if p.plugin_type == ptype)
                for ptype in PluginType
            },
            "total_hooks": len(self.hooks),
        }


# Global plugin manager
_plugin_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    """
    Get global plugin manager instance.

    Returns:
        Global PluginManager
    """
    global _plugin_manager

    if _plugin_manager is None:
        _plugin_manager = PluginManager()

    return _plugin_manager
