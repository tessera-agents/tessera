"""
Custom Pydantic Settings source for loading YAML configuration files.

Supports XDG Base Directory specification with hierarchical config merging.
"""

from pathlib import Path
from typing import Any, Dict, Tuple, Type, List
import yaml
import os

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from .xdg import get_tessera_config_dir
from ..logging_config import get_logger

logger = get_logger(__name__)


def get_config_paths(app_name: str = "tessera") -> List[Path]:
    """
    Get configuration file paths following XDG Base Directory spec.

    Returns paths in precedence order (highest first):
    1. Project local config (./tessera.yaml or ./config.yaml)
    2. User config (~/.config/tessera/config.yaml)
    3. System configs (/etc/xdg/tessera/config.yaml)

    Args:
        app_name: Application name for config directory

    Returns:
        List of config file paths that exist, in precedence order
    """
    paths = []

    # 1. Project local (highest precedence)
    local_config = Path.cwd() / f"{app_name}.yaml"
    if local_config.exists():
        paths.append(local_config)

    alt_local = Path.cwd() / "config.yaml"
    if alt_local.exists() and alt_local not in paths:
        paths.append(alt_local)

    # 2. User config
    user_config = get_tessera_config_dir() / "config.yaml"
    if user_config.exists():
        paths.append(user_config)

    # 3. System configs (XDG_CONFIG_DIRS)
    xdg_config_dirs = os.environ.get("XDG_CONFIG_DIRS", "/etc/xdg")
    for config_dir_str in xdg_config_dirs.split(":"):
        system_config = Path(config_dir_str) / app_name / "config.yaml"
        if system_config.exists():
            paths.append(system_config)

    return paths


class XDGYamlSettingsSource(PydanticBaseSettingsSource):
    """
    Settings source that loads from XDG-compliant YAML locations.

    Loads and merges configs from multiple locations:
    - /etc/xdg/tessera/config.yaml (system, lowest priority)
    - ~/.config/tessera/config.yaml (user)
    - ./tessera.yaml or ./config.yaml (project, highest priority)

    Later files override earlier files with deep merging for nested dicts.
    """

    def __init__(self, settings_cls: Type[BaseSettings], app_name: str = "tessera"):
        """
        Initialize YAML settings source.

        Args:
            settings_cls: Pydantic Settings class
            app_name: Application name for config directory lookup
        """
        super().__init__(settings_cls)
        self.app_name = app_name
        self._merged_data: Dict[str, Any] = {}

        # Get all config paths (reverse for merging - system first)
        config_paths = list(reversed(get_config_paths(app_name)))

        # Merge configs: later files override earlier
        for config_path in config_paths:
            try:
                with open(config_path, "r") as f:
                    data = yaml.safe_load(f) or {}
                    self._deep_merge(self._merged_data, data)
            except Exception as e:
                # Log but don't fail on config read errors
                logger.warning(f"Failed to load {config_path}: {e}")

    @staticmethod
    def _deep_merge(base: Dict, update: Dict) -> Dict:
        """
        Deep merge update dict into base dict.

        Args:
            base: Base dictionary to merge into
            update: Update dictionary to merge from

        Returns:
            Base dictionary with updates applied
        """
        for key, value in update.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                XDGYamlSettingsSource._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    def get_field_value(self, field_name: str) -> Tuple[Any, str, bool]:
        """
        Get field value from merged YAML data.

        Args:
            field_name: Name of the field to retrieve

        Returns:
            Tuple of (value, field_key, value_is_complex)
        """
        field_value = self._merged_data.get(field_name)
        return field_value, field_name, False

    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        """
        Prepare field value before validation.

        Args:
            field_name: Name of the field
            field: Field information
            value: Raw value from YAML
            value_is_complex: Whether value is complex type

        Returns:
            Prepared value ready for validation
        """
        return value

    def __call__(self) -> Dict[str, Any]:
        """
        Return all settings from merged YAML.

        Returns:
            Dictionary of all merged settings
        """
        return self._merged_data
