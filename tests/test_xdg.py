"""
Tests for XDG directory helpers.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch

from tessera.config.xdg import (
    get_xdg_config_home,
    get_xdg_cache_home,
    get_xdg_data_home,
    get_tessera_config_dir,
    get_tessera_cache_dir,
    get_tessera_data_dir,
    ensure_directories,
    get_config_file_path,
    get_metrics_db_path,
)


@pytest.mark.unit
class TestXDGHelpers:
    """Test XDG Base Directory helpers."""

    def test_get_xdg_config_home_default(self):
        """Test default config directory."""
        with patch.dict(os.environ, {}, clear=True):
            config_home = get_xdg_config_home()
            assert config_home == Path.home() / ".config"

    def test_get_xdg_config_home_custom(self):
        """Test custom config directory."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/custom/config"}):
            config_home = get_xdg_config_home()
            assert config_home == Path("/custom/config")

    def test_get_xdg_cache_home_default(self):
        """Test default cache directory."""
        with patch.dict(os.environ, {}, clear=True):
            cache_home = get_xdg_cache_home()
            assert cache_home == Path.home() / ".cache"

    def test_get_xdg_cache_home_custom(self):
        """Test custom cache directory."""
        with patch.dict(os.environ, {"XDG_CACHE_HOME": "/custom/cache"}):
            cache_home = get_xdg_cache_home()
            assert cache_home == Path("/custom/cache")

    def test_get_xdg_data_home_default(self):
        """Test default data directory."""
        with patch.dict(os.environ, {}, clear=True):
            data_home = get_xdg_data_home()
            assert data_home == Path.home() / ".local" / "share"

    def test_get_tessera_config_dir(self):
        """Test Tessera config directory."""
        with patch.dict(os.environ, {}, clear=True):
            config_dir = get_tessera_config_dir()
            assert config_dir == Path.home() / ".config" / "tessera"

    def test_get_tessera_cache_dir(self):
        """Test Tessera cache directory."""
        with patch.dict(os.environ, {}, clear=True):
            cache_dir = get_tessera_cache_dir()
            assert cache_dir == Path.home() / ".cache" / "tessera"

    def test_get_tessera_data_dir(self):
        """Test Tessera data directory."""
        with patch.dict(os.environ, {}, clear=True):
            data_dir = get_tessera_data_dir()
            assert data_dir == Path.home() / ".local" / "share" / "tessera"

    def test_get_config_file_path(self):
        """Test config file path."""
        path = get_config_file_path()
        assert path.name == "config.yaml"
        assert "tessera" in str(path)

    def test_get_metrics_db_path(self):
        """Test metrics database path."""
        path = get_metrics_db_path()
        assert path.name == "metrics.db"
        assert "tessera" in str(path)

    def test_ensure_directories_creates_structure(self):
        """Test ensure_directories creates all needed dirs."""
        dirs = ensure_directories()

        # Should return dict with all directory paths
        assert "config" in dirs
        assert "cache" in dirs
        assert "config_prompts" in dirs
        assert "cache_otel" in dirs

        # All should be Path objects
        for path in dirs.values():
            assert isinstance(path, Path)
