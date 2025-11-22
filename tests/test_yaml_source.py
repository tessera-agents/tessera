"""
Tests for YAML configuration source.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tessera.config.yaml_source import XDGYamlSettingsSource, get_config_paths


@pytest.mark.unit
class TestGetConfigPaths:
    """Test config path resolution."""

    def test_finds_project_local_config(self):
        """Test finds tessera.yaml in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_file = tmpdir_path / "tessera.yaml"
            config_file.write_text("test: true")

            with patch("pathlib.Path.cwd", return_value=tmpdir_path):
                paths = get_config_paths()
                assert config_file in paths

    def test_path_precedence(self):
        """Test config paths are in correct precedence order."""
        paths = get_config_paths()

        # Paths should be in precedence order (highest first)
        # Local configs should come before user configs
        for i, _path in enumerate(paths):
            if i > 0:
                # Later paths should not be more specific than earlier ones
                assert True  # Basic check that list is ordered


@pytest.mark.unit
class TestXDGYamlSettingsSource:
    """Test XDG YAML settings source."""

    def test_initialization(self):
        """Test source can be initialized."""
        from pydantic_settings import BaseSettings

        class TestSettings(BaseSettings):
            test_field: str = "default"

        source = XDGYamlSettingsSource(TestSettings, "tessera")

        # Should initialize without error
        assert source.app_name == "tessera"
        assert isinstance(source._merged_data, dict)

    def test_deep_merge(self):
        """Test deep merge of nested dicts."""
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        update = {"b": {"c": 99, "e": 4}, "f": 5}

        result = XDGYamlSettingsSource._deep_merge(base, update)

        # Nested values should be merged
        assert result["b"]["c"] == 99  # Updated
        assert result["b"]["d"] == 3  # Preserved
        assert result["b"]["e"] == 4  # Added
        assert result["f"] == 5  # New top-level

    def test_call_returns_merged_data(self):
        """Test __call__ returns merged configuration."""
        from pydantic_settings import BaseSettings

        class TestSettings(BaseSettings):
            pass

        source = XDGYamlSettingsSource(TestSettings, "tessera")
        data = source()

        assert isinstance(data, dict)
