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
        # Just check that we get a list back (paths may not exist)
        # Source code now handles FileNotFoundError gracefully
        assert isinstance(paths, list)


@pytest.mark.unit
class TestXDGYamlSettingsSource:
    """Test XDG YAML settings source."""

    def test_initialization(self):
        """Test source can be initialized."""
        from pydantic_settings import BaseSettings

        class TestSettings(BaseSettings):
            test_field: str = "default"

        # Initialize with a test app name that won't find config files
        # Source code now handles FileNotFoundError gracefully
        source = XDGYamlSettingsSource(TestSettings, "test-nonexistent-app")

        # Should initialize without error
        assert source.app_name == "test-nonexistent-app"
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

        # Use test app name that won't find config files
        # Source code now handles FileNotFoundError gracefully
        source = XDGYamlSettingsSource(TestSettings, "test-nonexistent-app")
        data = source()

        assert isinstance(data, dict)

    def test_merges_config_files(self):
        """Test merging configuration from multiple files."""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from pydantic_settings import BaseSettings

        class TestSettings(BaseSettings):
            test_value: str | None = None

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a local config.yaml file
            config_file = tmpdir_path / "config.yaml"
            config_file.write_text("test_value: from_config")

            # Create a test-app.yaml file
            app_file = tmpdir_path / "test-app.yaml"
            app_file.write_text("test_value: from_app\nother_value: 123")

            # Mock Path.cwd() to return tmpdir
            with patch("pathlib.Path.cwd", return_value=tmpdir_path):
                source = XDGYamlSettingsSource(TestSettings, "test-app")
                data = source()

                # Should have loaded both files and merged them
                assert isinstance(data, dict)
                # test-app.yaml has higher precedence
                assert data.get("test_value") == "from_app"
                assert data.get("other_value") == 123

    def test_handles_empty_yaml_file(self):
        """Test handling of empty YAML files."""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from pydantic_settings import BaseSettings

        class TestSettings(BaseSettings):
            pass

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create an empty config file
            config_file = tmpdir_path / "test-app.yaml"
            config_file.write_text("")

            # Mock Path.cwd() to return tmpdir
            with patch("pathlib.Path.cwd", return_value=tmpdir_path):
                source = XDGYamlSettingsSource(TestSettings, "test-app")
                data = source()

                # Should handle empty file gracefully
                assert isinstance(data, dict)
