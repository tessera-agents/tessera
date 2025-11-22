"""
Plugin loading from ~/.config/tessera/plugins/

Discovers and loads Python plugins from user directory.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any

from ..config.xdg import get_tessera_config_dir
from ..logging_config import get_logger
from .manager import Plugin, PluginManager, PluginType, get_plugin_manager

logger = get_logger(__name__)


class PluginLoader:
    """
    Loads plugins from filesystem.

    Scans plugin directory and loads Python modules.
    """

    def __init__(self, plugin_dir: Path | None = None) -> None:
        """
        Initialize plugin loader.

        Args:
            plugin_dir: Plugin directory (defaults to ~/.config/tessera/plugins)
        """
        if plugin_dir is None:
            plugin_dir = get_tessera_config_dir() / "plugins"

        self.plugin_dir = plugin_dir
        self.plugin_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"PluginLoader: {self.plugin_dir}")

    def discover_plugins(self) -> list[Path]:
        """
        Discover plugin files.

        Returns:
            List of plugin Python files
        """
        if not self.plugin_dir.exists():
            return []

        plugin_files = []

        # Find all .py files
        for py_file in self.plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue  # Skip private files

            plugin_files.append(py_file)

        # Find plugin packages
        for pkg_dir in self.plugin_dir.iterdir():
            if pkg_dir.is_dir() and not pkg_dir.name.startswith(("_", ".")):
                init_file = pkg_dir / "__init__.py"
                if init_file.exists():
                    plugin_files.append(init_file)

        logger.debug(f"Discovered {len(plugin_files)} plugin files")

        return plugin_files

    def load_plugin_module(self, plugin_file: Path) -> Any | None:
        """
        Load plugin module from file.

        Args:
            plugin_file: Path to plugin Python file

        Returns:
            Loaded module or None
        """
        try:
            # Generate module name
            module_name = f"tessera_plugin_{plugin_file.stem}"

            # Load module
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)

            if spec is None or spec.loader is None:
                logger.warning(f"Failed to create spec for {plugin_file}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            logger.debug(f"Loaded plugin module: {module_name}")

            return module

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_file}: {e}")
            return None

    def extract_plugin_info(self, module: Any) -> Plugin | None:
        """
        Extract plugin info from loaded module.

        Expected module attributes:
        - PLUGIN_NAME: str
        - PLUGIN_TYPE: str
        - PLUGIN_VERSION: str
        - PLUGIN_DESCRIPTION: str
        - plugin_entry_point: callable

        Args:
            module: Loaded plugin module

        Returns:
            Plugin instance or None
        """
        try:
            name = getattr(module, "PLUGIN_NAME", module.__name__)
            plugin_type_str = getattr(module, "PLUGIN_TYPE", "tool")
            version = getattr(module, "PLUGIN_VERSION", "0.1.0")
            description = getattr(module, "PLUGIN_DESCRIPTION", "No description")
            entry_point = getattr(module, "plugin_entry_point", None)
            config = getattr(module, "PLUGIN_CONFIG", {})

            if entry_point is None or not callable(entry_point):
                logger.warning(f"Plugin {name} missing callable plugin_entry_point")
                return None

            plugin_type = PluginType(plugin_type_str)

            plugin = Plugin(
                name=name,
                plugin_type=plugin_type,
                version=version,
                description=description,
                entry_point=entry_point,
                config=config,
            )

            logger.debug(f"Extracted plugin info: {name}")

            return plugin

        except Exception as e:
            logger.error(f"Failed to extract plugin info: {e}")
            return None

    def load_all_plugins(self, manager: PluginManager | None = None) -> int:
        """
        Load all plugins from plugin directory.

        Args:
            manager: Plugin manager (uses global if None)

        Returns:
            Number of plugins loaded
        """
        manager = manager or get_plugin_manager()

        plugin_files = self.discover_plugins()
        loaded_count = 0

        for plugin_file in plugin_files:
            # Load module
            module = self.load_plugin_module(plugin_file)

            if module is None:
                continue

            # Extract plugin info
            plugin = self.extract_plugin_info(module)

            if plugin is None:
                continue

            # Register with manager
            manager.register_plugin(plugin)
            loaded_count += 1

        logger.info(f"Loaded {loaded_count} plugins from {self.plugin_dir}")

        return loaded_count


def load_plugins() -> int:
    """
    Load all plugins using default loader.

    Returns:
        Number of plugins loaded
    """
    loader = PluginLoader()
    return loader.load_all_plugins()
