"""Tests for plugin loading functionality."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from tessera.plugins.loader import PluginLoader, load_plugins
from tessera.plugins.manager import PluginType


class TestPluginLoader:
    """Test plugin loader."""

    def test_initialization_default_dir(self) -> None:
        """Test loader initialization with default directory."""
        with patch("tessera.plugins.loader.get_tessera_config_dir") as mock_get_dir:
            mock_get_dir.return_value = Path("/tmp/tessera")

            loader = PluginLoader()

            assert loader.plugin_dir == Path("/tmp/tessera/plugins")

    def test_initialization_custom_dir(self, tmp_path: Path) -> None:
        """Test loader initialization with custom directory."""
        plugin_dir = tmp_path / "custom_plugins"

        loader = PluginLoader(plugin_dir=plugin_dir)

        assert loader.plugin_dir == plugin_dir
        assert plugin_dir.exists()

    def test_discover_plugins_empty_dir(self, tmp_path: Path) -> None:
        """Test discovering plugins in empty directory."""
        loader = PluginLoader(plugin_dir=tmp_path)

        plugins = loader.discover_plugins()

        assert plugins == []

    def test_discover_plugins_nonexistent_dir(self, tmp_path: Path) -> None:
        """Test discovering plugins in non-existent directory."""
        nonexistent = tmp_path / "nonexistent"

        loader = PluginLoader(plugin_dir=nonexistent)
        # Directory is created during init
        nonexistent.rmdir()

        plugins = loader.discover_plugins()

        assert plugins == []

    def test_discover_plugins_python_files(self, tmp_path: Path) -> None:
        """Test discovering Python plugin files."""
        (tmp_path / "plugin1.py").write_text("# Plugin 1")
        (tmp_path / "plugin2.py").write_text("# Plugin 2")
        (tmp_path / "_private.py").write_text("# Should be skipped")

        loader = PluginLoader(plugin_dir=tmp_path)

        plugins = loader.discover_plugins()

        assert len(plugins) == 2
        assert tmp_path / "plugin1.py" in plugins
        assert tmp_path / "plugin2.py" in plugins
        assert tmp_path / "_private.py" not in plugins

    def test_discover_plugins_packages(self, tmp_path: Path) -> None:
        """Test discovering plugin packages."""
        pkg1 = tmp_path / "plugin_pkg1"
        pkg1.mkdir()
        (pkg1 / "__init__.py").write_text("# Plugin package 1")

        pkg2 = tmp_path / "plugin_pkg2"
        pkg2.mkdir()
        (pkg2 / "__init__.py").write_text("# Plugin package 2")

        # Package without __init__.py should be skipped
        pkg3 = tmp_path / "not_a_package"
        pkg3.mkdir()

        # Hidden directories should be skipped
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "__init__.py").write_text("# Hidden")

        loader = PluginLoader(plugin_dir=tmp_path)

        plugins = loader.discover_plugins()

        assert len(plugins) == 2
        assert pkg1 / "__init__.py" in plugins
        assert pkg2 / "__init__.py" in plugins

    def test_load_plugin_module_success(self, tmp_path: Path) -> None:
        """Test successfully loading plugin module."""
        plugin_file = tmp_path / "test_plugin.py"
        plugin_file.write_text("TEST_VALUE = 42")

        loader = PluginLoader(plugin_dir=tmp_path)

        module = loader.load_plugin_module(plugin_file)

        assert module is not None
        assert hasattr(module, "TEST_VALUE")
        assert module.TEST_VALUE == 42

    def test_load_plugin_module_invalid_file(self, tmp_path: Path) -> None:
        """Test loading non-existent plugin file."""
        nonexistent = tmp_path / "nonexistent.py"

        loader = PluginLoader(plugin_dir=tmp_path)

        module = loader.load_plugin_module(nonexistent)

        assert module is None

    def test_load_plugin_module_import_error(self, tmp_path: Path) -> None:
        """Test loading plugin with import error."""
        plugin_file = tmp_path / "bad_plugin.py"
        plugin_file.write_text("import nonexistent_module")

        loader = PluginLoader(plugin_dir=tmp_path)

        module = loader.load_plugin_module(plugin_file)

        assert module is None

    @patch("tessera.plugins.loader.importlib.util.spec_from_file_location")
    def test_load_plugin_module_no_spec(self, mock_spec_from_file: Mock, tmp_path: Path) -> None:
        """Test loading plugin when spec creation fails."""
        plugin_file = tmp_path / "plugin.py"
        plugin_file.write_text("# Test")

        mock_spec_from_file.return_value = None

        loader = PluginLoader(plugin_dir=tmp_path)

        module = loader.load_plugin_module(plugin_file)

        assert module is None

    @patch("tessera.plugins.loader.importlib.util.spec_from_file_location")
    def test_load_plugin_module_no_loader(self, mock_spec_from_file: Mock, tmp_path: Path) -> None:
        """Test loading plugin when spec has no loader."""
        plugin_file = tmp_path / "plugin.py"
        plugin_file.write_text("# Test")

        mock_spec = MagicMock()
        mock_spec.loader = None
        mock_spec_from_file.return_value = mock_spec

        loader = PluginLoader(plugin_dir=tmp_path)

        module = loader.load_plugin_module(plugin_file)

        assert module is None

    def test_extract_plugin_info_full(self, tmp_path: Path) -> None:
        """Test extracting plugin info with all attributes."""
        plugin_file = tmp_path / "test_plugin.py"
        plugin_file.write_text(
            """
PLUGIN_NAME = "test-plugin"
PLUGIN_TYPE = "tool"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Test plugin"
PLUGIN_CONFIG = {"key": "value"}

def plugin_entry_point():
    return "test"
"""
        )

        loader = PluginLoader(plugin_dir=tmp_path)
        module = loader.load_plugin_module(plugin_file)

        plugin = loader.extract_plugin_info(module)

        assert plugin is not None
        assert plugin.name == "test-plugin"
        assert plugin.plugin_type == PluginType.TOOL
        assert plugin.version == "1.0.0"
        assert plugin.description == "Test plugin"
        assert plugin.config == {"key": "value"}
        assert callable(plugin.entry_point)

    def test_extract_plugin_info_minimal(self, tmp_path: Path) -> None:
        """Test extracting plugin info with minimal attributes."""
        plugin_file = tmp_path / "test_plugin.py"
        plugin_file.write_text(
            """
def plugin_entry_point():
    return "test"
"""
        )

        loader = PluginLoader(plugin_dir=tmp_path)
        module = loader.load_plugin_module(plugin_file)

        plugin = loader.extract_plugin_info(module)

        assert plugin is not None
        assert plugin.plugin_type == PluginType.TOOL  # Default
        assert plugin.version == "0.1.0"  # Default
        assert plugin.description == "No description"  # Default
        assert plugin.config == {}  # Default

    def test_extract_plugin_info_no_entry_point(self, tmp_path: Path) -> None:
        """Test extracting plugin info without entry point."""
        plugin_file = tmp_path / "test_plugin.py"
        plugin_file.write_text(
            """
PLUGIN_NAME = "test"
"""
        )

        loader = PluginLoader(plugin_dir=tmp_path)
        module = loader.load_plugin_module(plugin_file)

        plugin = loader.extract_plugin_info(module)

        assert plugin is None

    def test_extract_plugin_info_non_callable_entry_point(self, tmp_path: Path) -> None:
        """Test extracting plugin info with non-callable entry point."""
        plugin_file = tmp_path / "test_plugin.py"
        plugin_file.write_text(
            """
plugin_entry_point = "not a function"
"""
        )

        loader = PluginLoader(plugin_dir=tmp_path)
        module = loader.load_plugin_module(plugin_file)

        plugin = loader.extract_plugin_info(module)

        assert plugin is None

    def test_extract_plugin_info_invalid_type(self, tmp_path: Path) -> None:
        """Test extracting plugin info with invalid type."""
        plugin_file = tmp_path / "test_plugin.py"
        plugin_file.write_text(
            """
PLUGIN_TYPE = "invalid_type"

def plugin_entry_point():
    return "test"
"""
        )

        loader = PluginLoader(plugin_dir=tmp_path)
        module = loader.load_plugin_module(plugin_file)

        plugin = loader.extract_plugin_info(module)

        assert plugin is None

    def test_load_all_plugins_empty(self, tmp_path: Path) -> None:
        """Test loading all plugins from empty directory."""
        from tessera.plugins.manager import PluginManager

        manager = PluginManager()
        loader = PluginLoader(plugin_dir=tmp_path)

        count = loader.load_all_plugins(manager)

        assert count == 0
        assert len(manager.plugins) == 0

    def test_load_all_plugins_success(self, tmp_path: Path) -> None:
        """Test loading multiple plugins successfully."""
        from tessera.plugins.manager import PluginManager

        # Create valid plugin 1
        plugin1 = tmp_path / "plugin1.py"
        plugin1.write_text(
            """
PLUGIN_NAME = "plugin1"
PLUGIN_TYPE = "tool"

def plugin_entry_point():
    return "plugin1"
"""
        )

        # Create valid plugin 2
        plugin2 = tmp_path / "plugin2.py"
        plugin2.write_text(
            """
PLUGIN_NAME = "plugin2"
PLUGIN_TYPE = "workflow"

def plugin_entry_point():
    return "plugin2"
"""
        )

        # Create invalid plugin (no entry point)
        invalid = tmp_path / "invalid.py"
        invalid.write_text("PLUGIN_NAME = 'invalid'")

        manager = PluginManager()
        loader = PluginLoader(plugin_dir=tmp_path)

        count = loader.load_all_plugins(manager)

        assert count == 2
        assert len(manager.plugins) == 2
        assert "plugin1" in manager.plugins
        assert "plugin2" in manager.plugins

    def test_load_all_plugins_with_failed_loads(self, tmp_path: Path) -> None:
        """Test loading plugins with some failures."""
        from tessera.plugins.manager import PluginManager

        # Create valid plugin
        valid = tmp_path / "valid.py"
        valid.write_text(
            """
def plugin_entry_point():
    return "valid"
"""
        )

        # Create plugin with import error
        import_error = tmp_path / "bad_import.py"
        import_error.write_text("import nonexistent_module")

        manager = PluginManager()
        loader = PluginLoader(plugin_dir=tmp_path)

        count = loader.load_all_plugins(manager)

        assert count == 1
        assert len(manager.plugins) == 1

    def test_load_all_plugins_uses_default_manager(self, tmp_path: Path) -> None:
        """Test that load_all_plugins uses default manager when none provided."""
        plugin = tmp_path / "plugin.py"
        plugin.write_text(
            """
PLUGIN_NAME = "test"

def plugin_entry_point():
    return "test"
"""
        )

        with patch("tessera.plugins.loader.get_plugin_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager

            loader = PluginLoader(plugin_dir=tmp_path)
            loader.load_all_plugins()

            mock_get_manager.assert_called_once()
            mock_manager.register_plugin.assert_called_once()


class TestLoadPluginsConvenience:
    """Test convenience function for loading plugins."""

    def test_load_plugins_uses_default_loader(self) -> None:
        """Test that load_plugins uses default loader."""
        with patch("tessera.plugins.loader.PluginLoader") as mock_loader_class:
            mock_loader = MagicMock()
            mock_loader.load_all_plugins.return_value = 5
            mock_loader_class.return_value = mock_loader

            count = load_plugins()

            mock_loader_class.assert_called_once_with()
            mock_loader.load_all_plugins.assert_called_once_with()
            assert count == 5
