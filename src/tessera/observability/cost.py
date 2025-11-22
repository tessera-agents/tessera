"""
Cost calculation and tracking for LLM usage.

Maintains a pricing table for different models and calculates costs
based on token usage.
"""

import sqlite3
import re
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path

from ..config.xdg import get_metrics_db_path
from ..logging_config import get_logger

logger = get_logger(__name__)


class CostCalculator:
    """
    Calculate LLM costs based on token usage and model pricing.

    Uses a SQLite database to store and lookup model pricing.
    Supports pattern matching for model variations (e.g., gpt-4-* matches gpt-4-0613).
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize cost calculator.

        Args:
            db_path: Path to metrics database (default: ~/.cache/tessera/metrics.db)
        """
        self.db_path = db_path or get_metrics_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with pricing table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_pricing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model_name TEXT NOT NULL,
                model_pattern TEXT,
                prompt_price_per_1k REAL NOT NULL,
                completion_price_per_1k REAL NOT NULL,
                effective_date DATE NOT NULL,
                deprecated_date DATE,
                UNIQUE(provider, model_name, effective_date)
            )
        """)

        # Insert default pricing if table is empty
        count = cursor.execute("SELECT COUNT(*) FROM model_pricing").fetchone()[0]
        if count == 0:
            self._populate_default_pricing(cursor)

        conn.commit()
        conn.close()

    def _populate_default_pricing(self, cursor: sqlite3.Cursor) -> None:
        """Populate database with default model pricing."""
        default_pricing = [
            # OpenAI models (as of Nov 2024)
            ("openai", "gpt-4", "gpt-4.*", 0.03, 0.06, "2024-01-01"),
            ("openai", "gpt-4-turbo", "gpt-4-turbo.*", 0.01, 0.03, "2024-01-01"),
            ("openai", "gpt-4o", "gpt-4o.*", 0.005, 0.015, "2024-01-01"),
            ("openai", "gpt-4o-mini", "gpt-4o-mini.*", 0.00015, 0.0006, "2024-01-01"),
            ("openai", "gpt-3.5-turbo", "gpt-3.5-turbo.*", 0.0005, 0.0015, "2024-01-01"),
            # Anthropic models (as of Nov 2024)
            ("anthropic", "claude-3-opus", "claude-3-opus.*", 0.015, 0.075, "2024-01-01"),
            (
                "anthropic",
                "claude-3-sonnet",
                "claude-3-sonnet.*",
                0.003,
                0.015,
                "2024-01-01",
            ),
            (
                "anthropic",
                "claude-3-haiku",
                "claude-3-haiku.*",
                0.00025,
                0.00125,
                "2024-01-01",
            ),
            (
                "anthropic",
                "claude-3-5-sonnet",
                "claude-3-5-sonnet.*",
                0.003,
                0.015,
                "2024-01-01",
            ),
        ]

        for provider, model, pattern, prompt_price, completion_price, date in default_pricing:
            cursor.execute(
                """
                INSERT OR IGNORE INTO model_pricing
                (provider, model_name, model_pattern, prompt_price_per_1k,
                 completion_price_per_1k, effective_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (provider, model, pattern, prompt_price, completion_price, date),
            )

    def calculate(
        self, model: str, prompt_tokens: int, completion_tokens: int, provider: Optional[str] = None
    ) -> float:
        """
        Calculate cost in USD.

        Args:
            model: Model name (e.g., "gpt-4", "claude-3-sonnet")
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            provider: Optional provider name (openai, anthropic, etc.)

        Returns:
            Total cost in USD

        Example:
            >>> calc = CostCalculator()
            >>> cost = calc.calculate("gpt-4", 150, 75)
            >>> print(f"Cost: ${cost:.4f}")
            Cost: $0.0090
        """
        pricing = self._get_pricing(model, provider)

        if not pricing:
            # Unknown model - log warning and return 0
            logger.warning(f"No pricing found for model '{model}' (provider: {provider})")
            return 0.0

        prompt_cost = (prompt_tokens / 1000) * pricing["prompt_price"]
        completion_cost = (completion_tokens / 1000) * pricing["completion_price"]

        return round(prompt_cost + completion_cost, 6)

    def _get_pricing(self, model: str, provider: Optional[str]) -> Optional[Dict[str, float]]:
        """
        Fetch pricing from database with pattern matching.

        Args:
            model: Model name
            provider: Optional provider filter

        Returns:
            Dict with prompt_price and completion_price, or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Try exact match first
        query = """
            SELECT prompt_price_per_1k, completion_price_per_1k
            FROM model_pricing
            WHERE model_name = ?
              AND (? IS NULL OR provider = ?)
              AND (deprecated_date IS NULL OR deprecated_date > ?)
            ORDER BY effective_date DESC
            LIMIT 1
        """

        result = cursor.execute(query, (model, provider, provider, datetime.now().date().isoformat())).fetchone()

        if result:
            conn.close()
            return {"prompt_price": result[0], "completion_price": result[1]}

        # Try pattern matching
        query = """
            SELECT model_pattern, prompt_price_per_1k, completion_price_per_1k
            FROM model_pricing
            WHERE model_pattern IS NOT NULL
              AND (? IS NULL OR provider = ?)
              AND (deprecated_date IS NULL OR deprecated_date > ?)
        """

        patterns = cursor.execute(query, (provider, provider, datetime.now().date().isoformat())).fetchall()

        for pattern, prompt_price, completion_price in patterns:
            if re.match(pattern, model):
                conn.close()
                return {"prompt_price": prompt_price, "completion_price": completion_price}

        conn.close()
        return None

    def add_pricing(
        self,
        provider: str,
        model_name: str,
        prompt_price_per_1k: float,
        completion_price_per_1k: float,
        model_pattern: Optional[str] = None,
    ) -> None:
        """
        Add or update model pricing.

        Args:
            provider: Provider name (openai, anthropic, etc.)
            model_name: Model name
            prompt_price_per_1k: Price per 1K prompt tokens in USD
            completion_price_per_1k: Price per 1K completion tokens in USD
            model_pattern: Optional regex pattern for matching model variants
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO model_pricing
            (provider, model_name, model_pattern, prompt_price_per_1k,
             completion_price_per_1k, effective_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                provider,
                model_name,
                model_pattern,
                prompt_price_per_1k,
                completion_price_per_1k,
                datetime.now().date().isoformat(),
            ),
        )

        conn.commit()
        conn.close()
