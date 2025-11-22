"""
Premium model detection for GitHub Copilot.

Automatically fetches and parses the official GitHub Copilot documentation
to determine which models count as premium requests and their multipliers.

Note: GitHub docs don't provide Last-Modified or ETag headers, so we use
content-based change detection (hash comparison) to avoid unnecessary cache updates.
"""

import re
import time
import hashlib
from typing import Dict, Optional, Set, Tuple
from pathlib import Path
import json
import requests

from .logging_config import get_logger

logger = get_logger(__name__)


# Cache configuration
CACHE_FILE = Path(".cache/premium_models.json")
CACHE_TTL_HOURS = 24  # Refresh every 24 hours

# GitHub Copilot documentation URL
DOCS_URL = "https://docs.github.com/en/copilot/concepts/billing/copilot-requests"


class PremiumModelInfo:
    """Information about premium models and their multipliers."""

    def __init__(self):
        self._premium_models: Dict[str, float] = {}
        self._free_models: Set[str] = set()
        self._last_updated: float = 0.0
        self._content_hash: Optional[str] = None  # Hash of parsed content for change detection
        self._load_cache()

    def _load_cache(self) -> bool:
        """Load cached premium model data if available and fresh."""
        if not CACHE_FILE.exists():
            return False

        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)

            # Check if cache is still fresh
            cache_age = time.time() - data.get("timestamp", 0)
            if cache_age > CACHE_TTL_HOURS * 3600:
                return False

            self._premium_models = data.get("premium_models", {})
            self._free_models = set(data.get("free_models", []))
            self._last_updated = data.get("timestamp", 0)
            self._content_hash = data.get("content_hash")
            return True

        except (json.JSONDecodeError, KeyError, IOError):
            return False

    def _save_cache(self):
        """Save premium model data to cache."""
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "premium_models": self._premium_models,
            "free_models": list(self._free_models),
            "timestamp": self._last_updated,
            "content_hash": self._content_hash,
        }

        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def fetch_from_docs(self) -> bool:
        """
        Fetch and parse premium model information from GitHub docs.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch the documentation page
            response = requests.get(DOCS_URL, timeout=10)
            if response.status_code != 200:
                return False

            html = response.text

            # Parse the model multipliers table
            # The table structure is:
            # <tr><th scope="row">Model Name</th><td>Multiplier (paid)</td><td>Multiplier (free)</td></tr>

            # Extract table rows from model-multipliers section
            table_pattern = r'<h2 id="model-multipliers".*?<table>(.*?)</table>'
            table_match = re.search(table_pattern, html, re.DOTALL)

            if not table_match:
                # Fallback to hardcoded values if table not found
                logger.warning("Model multipliers table not found in docs, using fallback values")
                self._use_fallback_values()
                self._last_updated = time.time()
                self._save_cache()
                return True

            table_html = table_match.group(1)

            # Compute content hash for change detection
            # Hash only the table content (not the full page) to detect actual model changes
            new_hash = hashlib.sha256(table_html.encode()).hexdigest()

            # If content hasn't changed, skip parsing and cache update
            if self._content_hash == new_hash:
                # Content is identical, no need to re-parse or update cache
                return True

            # Content changed, parse the table
            # Parse each table row
            row_pattern = r'<tr><th scope="row">(.*?)</th><td>(.*?)</td><td>(.*?)</td></tr>'
            rows = re.findall(row_pattern, table_html, re.DOTALL)

            # Clear existing data before parsing new content
            self._premium_models.clear()
            self._free_models.clear()

            parsed_count = 0
            for model_name, multiplier_paid, multiplier_free in rows:
                model_name = model_name.strip()
                multiplier_paid = multiplier_paid.strip()

                # Normalize model name to API format
                normalized = self._normalize_model_name(model_name)
                if not normalized:
                    continue

                # Parse multiplier (paid plans)
                try:
                    mult = float(multiplier_paid)

                    # If multiplier is 0, it's a free model
                    if mult == 0:
                        self._free_models.add(normalized)
                    else:
                        # Premium model
                        self._premium_models[normalized] = mult

                    parsed_count += 1
                except ValueError:
                    # Skip if multiplier is not a number (e.g., "Not applicable")
                    continue

            # If we didn't parse any models, use fallback
            if parsed_count == 0:
                logger.warning("No models parsed from docs, using fallback values")
                self._use_fallback_values()

            # Save the new content hash and update timestamp
            self._content_hash = new_hash
            self._last_updated = time.time()
            self._save_cache()
            return True

        except Exception as e:
            logger.warning(f"Failed to fetch premium model info: {e}")
            return False

    def _use_fallback_values(self):
        """Use hardcoded fallback values when parsing fails."""
        self._free_models = {"gpt-5-mini", "gpt-4.1", "gpt-4o"}
        self._premium_models = {
            "claude-haiku-4.5": 0.33,
            "grok-code-fast-1": 0.25,
            "claude-3.5-sonnet": 1.0,
            "claude-sonnet-4": 1.0,
            "claude-sonnet-4.5": 1.0,
            "gemini-2.5-pro": 1.0,
            "gpt-5": 1.0,
            "gpt-5-codex": 1.0,
            "claude-opus-4.1": 10.0,
        }

    def _normalize_model_name(self, name: str) -> Optional[str]:
        """
        Normalize model name from documentation to API format.

        Args:
            name: Model name from documentation (e.g., "GPT-5 mini", "Claude Sonnet 3.5")

        Returns:
            Normalized model ID matching API format, or None if unknown
        """
        name = name.lower().strip()

        # Mapping of documentation names to API IDs
        mappings = {
            "gpt-5 mini": "gpt-5-mini",
            "gpt 5 mini": "gpt-5-mini",
            "gpt-4.1": "gpt-4.1",
            "gpt 4.1": "gpt-4.1",
            "gpt-4o": "gpt-4o",
            "gpt 4o": "gpt-4o",
            "gpt-5": "gpt-5",
            "gpt 5": "gpt-5",
            "gpt-5-codex": "gpt-5-codex",
            "gpt 5 codex": "gpt-5-codex",
            "claude sonnet 3.5": "claude-3.5-sonnet",
            "claude 3.5 sonnet": "claude-3.5-sonnet",
            "claude sonnet 4": "claude-sonnet-4",
            "claude sonnet 4.5": "claude-sonnet-4.5",
            "claude haiku 4.5": "claude-haiku-4.5",
            "claude opus 4.1": "claude-opus-4.1",
            "gemini 2.5 pro": "gemini-2.5-pro",
            "grok code fast 1": "grok-code-fast-1",
        }

        return mappings.get(name)

    def ensure_loaded(self):
        """Ensure premium model data is loaded, fetching if necessary."""
        if not self._premium_models and not self._free_models:
            # Try to load from cache first
            if not self._load_cache():
                # Cache miss or stale, fetch from docs
                self.fetch_from_docs()

    def is_premium(self, model_id: str) -> bool:
        """
        Check if a model consumes premium requests.

        Args:
            model_id: Model ID (e.g., "gpt-4", "claude-3.5-sonnet")

        Returns:
            True if model consumes premium requests, False otherwise
        """
        self.ensure_loaded()

        # Normalize model ID
        model_id = model_id.lower().strip()

        # Check if explicitly free
        if model_id in self._free_models:
            return False

        # Check if explicitly premium
        if model_id in self._premium_models:
            return True

        # Legacy models (not in current docs) - assume free to be safe
        # This includes gpt-4, gpt-3.5-turbo, etc.
        return False

    def get_multiplier(self, model_id: str) -> float:
        """
        Get the premium request multiplier for a model.

        Args:
            model_id: Model ID

        Returns:
            Multiplier (e.g., 1.0, 10.0), or 0.0 if free
        """
        self.ensure_loaded()

        model_id = model_id.lower().strip()

        if model_id in self._free_models:
            return 0.0

        return self._premium_models.get(model_id, 0.0)

    def get_all_premium_models(self) -> Dict[str, float]:
        """
        Get all premium models and their multipliers.

        Returns:
            Dictionary mapping model IDs to multipliers
        """
        self.ensure_loaded()
        return self._premium_models.copy()

    def get_all_free_models(self) -> Set[str]:
        """
        Get all free (unlimited) models.

        Returns:
            Set of free model IDs
        """
        self.ensure_loaded()
        return self._free_models.copy()


# Global singleton instance
_premium_info: Optional[PremiumModelInfo] = None


def get_premium_info() -> PremiumModelInfo:
    """Get the global PremiumModelInfo singleton."""
    global _premium_info
    if _premium_info is None:
        _premium_info = PremiumModelInfo()
    return _premium_info


def is_premium_model(model_id: str) -> bool:
    """
    Check if a model consumes premium requests.

    Args:
        model_id: Model ID (e.g., "gpt-4", "claude-3.5-sonnet")

    Returns:
        True if model consumes premium requests
    """
    return get_premium_info().is_premium(model_id)


def get_model_multiplier(model_id: str) -> float:
    """
    Get the premium request multiplier for a model.

    Args:
        model_id: Model ID

    Returns:
        Multiplier (e.g., 1.0, 10.0), or 0.0 if free
    """
    return get_premium_info().get_multiplier(model_id)


def refresh_premium_models() -> bool:
    """
    Force refresh of premium model information from GitHub docs.

    Returns:
        True if successful
    """
    return get_premium_info().fetch_from_docs()
