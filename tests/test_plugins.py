"""Tests for plugin system."""

import pytest

from tessera.plugins.manager import Plugin, PluginManager, PluginType


@pytest.mark.unit
class TestPluginManager:
    """Test plugin manager functionality."""

    def test_manager_initialization(self):
        """Test initializing plugin manager."""
        manager = PluginManager()

        assert manager.plugins == {}
        assert manager.hooks == {}

    def test_register_plugin(self):
        """Test registering a plugin."""
        manager = PluginManager()

        plugin = Plugin(
            name="test-plugin",
            plugin_type=PluginType.TOOL,
            version="1.0.0",
            description="Test plugin",
            entry_point=lambda: "test",
            config={},
        )

        manager.register_plugin(plugin)

        assert "test-plugin" in manager.plugins
        assert manager.plugins["test-plugin"] == plugin

    def test_unregister_plugin(self):
        """Test unregistering plugin."""
        manager = PluginManager()

        plugin = Plugin(
            name="test",
            plugin_type=PluginType.AGENT,
            version="1.0.0",
            description="Test",
            entry_point=lambda: None,
            config={},
        )

        manager.register_plugin(plugin)
        success = manager.unregister_plugin("test")

        assert success is True
        assert "test" not in manager.plugins

    def test_get_plugin(self):
        """Test getting plugin by name."""
        manager = PluginManager()

        plugin = Plugin(
            name="my-plugin",
            plugin_type=PluginType.WORKFLOW,
            version="2.0.0",
            description="My plugin",
            entry_point=lambda: "result",
            config={},
        )

        manager.register_plugin(plugin)

        retrieved = manager.get_plugin("my-plugin")

        assert retrieved is not None
        assert retrieved.name == "my-plugin"

    def test_list_plugins(self):
        """Test listing all plugins."""
        manager = PluginManager()

        p1 = Plugin("p1", PluginType.TOOL, "1.0", "Desc", lambda: None, {})
        p2 = Plugin("p2", PluginType.AGENT, "1.0", "Desc", lambda: None, {})
        p3 = Plugin("p3", PluginType.TOOL, "1.0", "Desc", lambda: None, {})

        manager.register_plugin(p1)
        manager.register_plugin(p2)
        manager.register_plugin(p3)

        all_plugins = manager.list_plugins()
        assert len(all_plugins) == 3

        tool_plugins = manager.list_plugins(plugin_type=PluginType.TOOL)
        assert len(tool_plugins) == 2

    def test_enable_disable_plugin(self):
        """Test enabling and disabling plugins."""
        manager = PluginManager()

        plugin = Plugin("test", PluginType.TOOL, "1.0", "Test", lambda: None, {})
        manager.register_plugin(plugin)

        # Disable
        success = manager.disable_plugin("test")
        assert success is True
        assert plugin.enabled is False

        # Enable
        success = manager.enable_plugin("test")
        assert success is True
        assert plugin.enabled is True

    def test_register_hook(self):
        """Test registering hook callbacks."""
        manager = PluginManager()

        def my_hook():
            return "hook_result"

        manager.register_hook("before_execute", my_hook)

        assert "before_execute" in manager.hooks
        assert my_hook in manager.hooks["before_execute"]

    def test_execute_hooks(self):
        """Test executing hook callbacks."""
        manager = PluginManager()

        results = []

        def hook1(value):
            results.append(f"hook1:{value}")
            return "result1"

        def hook2(value):
            results.append(f"hook2:{value}")
            return "result2"

        manager.register_hook("test_hook", hook1)
        manager.register_hook("test_hook", hook2)

        hook_results = manager.execute_hooks("test_hook", "test_value")

        assert len(hook_results) == 2
        assert "hook1:test_value" in results
        assert "hook2:test_value" in results

    def test_get_stats(self):
        """Test getting plugin statistics."""
        manager = PluginManager()

        p1 = Plugin("p1", PluginType.TOOL, "1.0", "Desc", lambda: None, {})
        p2 = Plugin("p2", PluginType.AGENT, "1.0", "Desc", lambda: None, {})

        manager.register_plugin(p1)
        manager.register_plugin(p2)
        manager.disable_plugin("p1")

        stats = manager.get_stats()

        assert stats["total_plugins"] == 2
        assert stats["enabled_plugins"] == 1
        assert stats["disabled_plugins"] == 1
        assert stats["by_type"][PluginType.TOOL.value] == 1
