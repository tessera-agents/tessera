"""
Logging configuration for Tessera.

Provides a simple interface for setting up structured logging across the codebase.
"""

import logging
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure logging for Tessera.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to WARNING for library usage, INFO for CLI.
    """
    log_level = level or "WARNING"

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure root logger
    root_logger = logging.getLogger("tessera")
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Add console handler if not already present
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger instance
    """
    # Ensure setup has been called
    if not logging.getLogger("tessera").handlers:
        setup_logging()

    return logging.getLogger(f"tessera.{name}")
