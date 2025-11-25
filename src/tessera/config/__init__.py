"""
Tessera configuration module.
"""

# XDG helpers
# Re-export original config classes for backward compatibility
from tessera.legacy_config import (
    INTERVIEWER_PROMPT,
    SUPERVISOR_PROMPT,
    FrameworkConfig,
    LLMConfig,
    ScoringWeights,
)

# Unified config schema
from .schema import TesseraSettings
from .xdg import (
    ensure_directories,
    get_config_file_path,
    get_metrics_db_path,
    get_tessera_cache_dir,
    get_tessera_config_dir,
    get_xdg_cache_home,
    get_xdg_config_home,
    get_xdg_data_home,
)

__all__ = [
    "INTERVIEWER_PROMPT",
    "SUPERVISOR_PROMPT",
    "FrameworkConfig",
    # Legacy (backward compat)
    "LLMConfig",
    "ScoringWeights",
    # Schemas
    "TesseraSettings",
    "ensure_directories",
    "get_config_file_path",
    "get_metrics_db_path",
    "get_tessera_cache_dir",
    "get_tessera_config_dir",
    "get_xdg_cache_home",
    # XDG
    "get_xdg_config_home",
    "get_xdg_data_home",
]
