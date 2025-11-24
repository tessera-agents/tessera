"""
Base utilities for LangGraph integration.

Provides shared checkpointing, state management, and utilities
for all LangGraph-based agents.
"""

import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

# Default checkpoint database location
CHECKPOINT_DB = Path(".cache/langgraph_checkpoints.db")

# Global checkpointer instance and connection
_checkpointer: SqliteSaver | None = None
_conn: sqlite3.Connection | None = None


def get_checkpointer(db_path: Path | None = None) -> SqliteSaver:
    """
    Get the global SQLite checkpointer instance.

    Args:
        db_path: Optional custom database path (uses default if None)

    Returns:
        SqliteSaver: Configured checkpointer

    Example:
        >>> from tessera.graph_base import get_checkpointer
        >>> checkpointer = get_checkpointer()
        >>> app = workflow.compile(checkpointer=checkpointer)
    """
    global _checkpointer, _conn

    # Use custom path if provided, otherwise use default
    path = db_path or CHECKPOINT_DB

    # Create checkpointer if not exists or path changed
    if _checkpointer is None:
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Create SQLite connection
        _conn = sqlite3.connect(str(path), check_same_thread=False)

        # Create SQLite checkpointer
        _checkpointer = SqliteSaver(_conn)

    return _checkpointer


def reset_checkpointer() -> None:
    """
    Reset the global checkpointer instance.

    Useful for testing or when switching databases.

    Example:
        >>> from tessera.graph_base import reset_checkpointer
        >>> reset_checkpointer()
    """
    global _checkpointer, _conn

    # Close the connection if it exists
    if _conn is not None:
        _conn.close()
        _conn = None

    _checkpointer = None


def get_thread_config(thread_id: str) -> dict:
    """
    Create a configuration dictionary for a specific thread.

    Args:
        thread_id: Unique identifier for this conversation/task thread

    Returns:
        dict: Configuration dictionary for LangGraph invoke/stream

    Example:
        >>> config = get_thread_config("project-123")
        >>> result = app.invoke({"objective": "..."}, config=config)
        >>>
        >>> # Resume from checkpoint
        >>> result = app.invoke(None, config=config)
    """
    return {
        "configurable": {
            "thread_id": thread_id,
        }
    }


def clear_checkpoint_db(db_path: Path | None = None) -> None:
    """
    Delete the checkpoint database file.

    WARNING: This will erase all saved state!

    Args:
        db_path: Optional custom database path (uses default if None)

    Example:
        >>> from tessera.graph_base import clear_checkpoint_db
        >>> clear_checkpoint_db()  # Delete all checkpoints
    """
    path = db_path or CHECKPOINT_DB

    if path.exists():
        path.unlink()

    # Reset the global checkpointer
    reset_checkpointer()
