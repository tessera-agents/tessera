"""
XDG Base Directory Specification support.

Follows the XDG Base Directory specification for storing configuration,
cache, and data files in standard locations.

References:
    https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
"""

import os
from pathlib import Path

APP_NAME = "tessera"


def get_xdg_config_home() -> Path:
    """
    Get the XDG config directory.

    Returns:
        Path to config directory (default: ~/.config)

    Environment:
        XDG_CONFIG_HOME: Override default config directory
    """
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config)
    return Path.home() / ".config"


def get_xdg_cache_home() -> Path:
    """
    Get the XDG cache directory.

    Returns:
        Path to cache directory (default: ~/.cache)

    Environment:
        XDG_CACHE_HOME: Override default cache directory
    """
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache)
    return Path.home() / ".cache"


def get_xdg_data_home() -> Path:
    """
    Get the XDG data directory.

    Returns:
        Path to data directory (default: ~/.local/share)

    Environment:
        XDG_DATA_HOME: Override default data directory
    """
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data)
    return Path.home() / ".local" / "share"


def get_tessera_config_dir() -> Path:
    """
    Get Tessera's configuration directory.

    Returns:
        Path to ~/.config/tessera (or XDG_CONFIG_HOME/tessera)
    """
    return get_xdg_config_home() / APP_NAME


def get_tessera_cache_dir() -> Path:
    """
    Get Tessera's cache directory.

    Returns:
        Path to ~/.cache/tessera (or XDG_CACHE_HOME/tessera)
    """
    return get_xdg_cache_home() / APP_NAME


def get_tessera_data_dir() -> Path:
    """
    Get Tessera's data directory.

    Returns:
        Path to ~/.local/share/tessera (or XDG_DATA_HOME/tessera)
    """
    return get_xdg_data_home() / APP_NAME


def ensure_directories() -> dict[str, Path]:
    """
    Ensure all Tessera directories exist.

    Creates directories if they don't exist:
    - ~/.config/tessera/
    - ~/.config/tessera/prompts/
    - ~/.config/tessera/plugins/
    - ~/.cache/tessera/
    - ~/.cache/tessera/otel/
    - ~/.local/share/tessera/
    - ~/.local/share/tessera/queue/

    Returns:
        Dictionary with all directory paths
    """
    config_dir = get_tessera_config_dir()
    cache_dir = get_tessera_cache_dir()
    data_dir = get_tessera_data_dir()

    # Create directory structure
    (config_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (config_dir / "plugins").mkdir(parents=True, exist_ok=True)
    (cache_dir / "otel").mkdir(parents=True, exist_ok=True)
    (data_dir / "queue").mkdir(parents=True, exist_ok=True)

    return {
        "config": config_dir,
        "config_prompts": config_dir / "prompts",
        "config_plugins": config_dir / "plugins",
        "cache": cache_dir,
        "cache_otel": cache_dir / "otel",
        "data": data_dir,
        "data_queue": data_dir / "queue",
    }


def get_config_file_path() -> Path:
    """
    Get path to main configuration file.

    Returns:
        Path to ~/.config/tessera/config.yaml
    """
    return get_tessera_config_dir() / "config.yaml"


def get_metrics_db_path() -> Path:
    """
    Get path to metrics database.

    Returns:
        Path to ~/.cache/tessera/metrics.db
    """
    return get_tessera_cache_dir() / "metrics.db"


def get_state_db_path() -> Path:
    """
    Get path to state database.

    Returns:
        Path to ~/.cache/tessera/state.db
    """
    return get_tessera_cache_dir() / "state.db"


def get_otel_traces_path() -> Path:
    """
    Get path to OTEL traces file.

    Returns:
        Path to ~/.cache/tessera/otel/traces.jsonl
    """
    return get_tessera_cache_dir() / "otel" / "traces.jsonl"
