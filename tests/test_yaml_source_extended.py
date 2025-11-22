"""Extended YAML source tests for coverage."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tessera.config.yaml_source import XDGYamlSettingsSource, get_config_paths


@pytest.mark.unit
class TestYAMLSourceExtended:
    """Extended YAML source tests."""

    def test_get_config_paths_includes_local(self):
        """Test config paths include local directory."""
        paths = get_config_paths()

        # Should include local tessera.yaml
        assert any("tessera.yaml" in str(p) or "tessera.yml" in str(p) for p in paths)

    def test_yaml_source_handles_missing_files(self):
        """Test YAML source handles missing config files gracefully."""
        from pydantic_settings import BaseSettings

        class TestSettings(BaseSettings):
            test_value: str = "default"

        source = XDGYamlSettingsSource(TestSettings, app_name="nonexistent_app_12345")

        # Should initialize without error even if no files exist
        assert source.app_name == "nonexistent_app_12345"
        assert isinstance(source._merged_data, dict)

    def test_yaml_source_with_actual_yaml(self):
        """Test YAML source loads actual YAML content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test.yaml"
            config_file.write_text("test_value: from_yaml\nnested:\n  key: value\n")

            from pydantic_settings import BaseSettings

            class TestSettings(BaseSettings):
                test_value: str = "default"

            # Mock get_config_paths to return our test file
            with patch("tessera.config.yaml_source.get_config_paths", return_value=[config_file]):
                source = XDGYamlSettingsSource(TestSettings)

                data = source()

                assert data.get("test_value") == "from_yaml"
                assert data.get("nested", {}).get("key") == "value"


@pytest.mark.unit
class TestDeepMerge:
    """Test deep merge functionality."""

    def test_deep_merge_nested_dicts(self):
        """Test deep merging nested dictionaries."""
        base = {
            "level1": {
                "level2": {
                    "keep_this": "value1",
                    "override_this": "old",
                },
                "keep_level2": "value2",
            },
        }

        update = {
            "level1": {
                "level2": {
                    "override_this": "new",
                    "add_this": "value3",
                },
            },
        }

        result = XDGYamlSettingsSource._deep_merge(base, update)

        assert result["level1"]["level2"]["keep_this"] == "value1"
        assert result["level1"]["level2"]["override_this"] == "new"
        assert result["level1"]["level2"]["add_this"] == "value3"
        assert result["level1"]["keep_level2"] == "value2"

    def test_deep_merge_list_replacement(self):
        """Test that lists are replaced, not merged."""
        base = {"items": [1, 2, 3]}
        update = {"items": [4, 5]}

        result = XDGYamlSettingsSource._deep_merge(base, update)

        assert result["items"] == [4, 5]  # Replaced, not merged

    def test_deep_merge_empty_update(self):
        """Test merging with empty update."""
        base = {"key": "value"}
        update = {}

        result = XDGYamlSettingsSource._deep_merge(base, update)

        assert result == {"key": "value"}
