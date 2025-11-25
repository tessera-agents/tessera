"""
Interview result caching for agent capabilities.

Caches interview results to avoid re-interviewing agents unnecessarily.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .config.xdg import get_tessera_cache_dir
from .logging_config import get_logger

logger = get_logger(__name__)

# Re-interview thresholds
_FAILURE_THRESHOLD = 3  # Re-interview after 3 failures
_OFF_TOPIC_THRESHOLD = 2  # Re-interview after 2 off-topic responses


class InterviewCache:
    """
    Caches agent interview results.

    Stores interview responses and capabilities to avoid redundant interviews.
    """

    def __init__(self, cache_file: Path | None = None, ttl_hours: int = 168) -> None:
        """
        Initialize interview cache.

        Args:
            cache_file: Path to cache file (defaults to XDG cache)
            ttl_hours: Time-to-live in hours (default: 1 week)
        """
        if cache_file is None:
            cache_dir = get_tessera_cache_dir()
            cache_file = cache_dir / "interview_cache.json"

        self.cache_file = cache_file
        self.ttl = timedelta(hours=ttl_hours)
        self._cache: dict[str, Any] = {}
        self._load_cache()

        logger.debug(f"InterviewCache: {self.cache_file}, TTL: {ttl_hours}h")

    def _load_cache(self) -> None:
        """Load cache from disk."""
        if not self.cache_file.exists():
            self._cache = {}
            return

        try:
            with self.cache_file.open() as f:
                self._cache = json.load(f)

            # Clean expired entries
            self._clean_expired()

        except (OSError, ValueError):
            logger.warning(f"Failed to load interview cache from {self.cache_file}")
            self._cache = {}

    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            with self.cache_file.open("w") as f:
                json.dump(self._cache, f, indent=2)

        except OSError:
            logger.warning(f"Failed to save interview cache to {self.cache_file}")

    def _clean_expired(self) -> None:
        """Remove expired cache entries."""
        now = datetime.now(UTC)
        expired_keys = []

        for key, entry in self._cache.items():
            try:
                cached_at = datetime.fromisoformat(entry.get("cached_at", ""))
                if now - cached_at > self.ttl:
                    expired_keys.append(key)
            except (ValueError, TypeError):
                expired_keys.append(key)  # Invalid timestamp

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
            self._save_cache()

    def _generate_key(self, agent_name: str, config_hash: str) -> str:
        """
        Generate cache key.

        Args:
            agent_name: Agent name
            config_hash: Hash of agent configuration

        Returns:
            Cache key
        """
        return f"{agent_name}:{config_hash}"

    def get(self, agent_name: str, config_hash: str) -> dict[str, Any] | None:
        """
        Get cached interview result.

        Args:
            agent_name: Agent name
            config_hash: Hash of agent configuration

        Returns:
            Cached interview result or None
        """
        key = self._generate_key(agent_name, config_hash)
        entry = self._cache.get(key)

        if entry is None:
            return None

        # Check if expired
        try:
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if datetime.now(UTC) - cached_at > self.ttl:
                del self._cache[key]
                self._save_cache()
                return None
        except (ValueError, TypeError, KeyError):
            return None

        logger.debug(f"Cache hit for {agent_name}")
        return entry.get("result")

    def set(self, agent_name: str, config_hash: str, interview_result: dict[str, Any]) -> None:
        """
        Cache interview result.

        Args:
            agent_name: Agent name
            config_hash: Hash of agent configuration
            interview_result: Interview result to cache
        """
        key = self._generate_key(agent_name, config_hash)

        self._cache[key] = {
            "agent_name": agent_name,
            "config_hash": config_hash,
            "cached_at": datetime.now(UTC).isoformat(),
            "result": interview_result,
        }

        self._save_cache()
        logger.debug(f"Cached interview for {agent_name}")

    def invalidate(self, agent_name: str) -> int:
        """
        Invalidate all cache entries for an agent.

        Args:
            agent_name: Agent name

        Returns:
            Number of entries invalidated
        """
        keys_to_remove = [key for key in self._cache if self._cache[key].get("agent_name") == agent_name]

        for key in keys_to_remove:
            del self._cache[key]

        if keys_to_remove:
            self._save_cache()
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for {agent_name}")

        return len(keys_to_remove)

    def clear(self) -> None:
        """Clear entire cache."""
        self._cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()

        logger.info("Cleared interview cache")

    def should_reinterview(
        self,
        agent_name: str,
        config_hash: str,
        recent_failures: int = 0,
        off_topic_count: int = 0,
    ) -> tuple[bool, str]:
        """
        Determine if agent should be re-interviewed.

        Args:
            agent_name: Agent name
            config_hash: Hash of agent configuration
            recent_failures: Number of recent task failures
            off_topic_count: Number of off-topic responses

        Returns:
            Tuple of (should_reinterview, reason)
        """
        # Check if cached
        cached = self.get(agent_name, config_hash)

        if cached is None:
            return (True, "no_cached_interview")

        # Re-interview triggers
        if recent_failures >= _FAILURE_THRESHOLD:
            return (True, f"high_failure_rate ({recent_failures} failures)")

        if off_topic_count >= _OFF_TOPIC_THRESHOLD:
            return (True, f"frequent_off_topic ({off_topic_count} times)")

        return (False, "cached_interview_valid")

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        self._clean_expired()

        return {
            "total_entries": len(self._cache),
            "agents_cached": len({entry["agent_name"] for entry in self._cache.values()}),
            "cache_file": str(self.cache_file),
            "ttl_hours": self.ttl.total_seconds() / 3600,
        }


# Global interview cache
_interview_cache: InterviewCache | None = None


def get_interview_cache() -> InterviewCache:
    """
    Get global interview cache instance.

    Returns:
        Global InterviewCache
    """
    global _interview_cache

    if _interview_cache is None:
        _interview_cache = InterviewCache()

    return _interview_cache
