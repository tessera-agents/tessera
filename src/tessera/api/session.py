"""
Session management for background execution and attach/detach.

Allows starting tasks in background, detaching, and re-attaching later.
"""

import asyncio
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..config.xdg import get_tessera_cache_dir
from ..logging_config import get_logger

logger = get_logger(__name__)


class SessionStatus(Enum):
    """Session execution status."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Session:
    """
    Execution session for background task execution.

    Supports attach/detach, pause/resume, and dynamic task addition.
    """

    def __init__(
        self,
        session_id: str | None = None,
        objective: str = "",
        created_at: datetime | None = None,
    ) -> None:
        """
        Initialize session.

        Args:
            session_id: Unique session ID (generated if None)
            objective: Task objective
            created_at: Creation timestamp
        """
        self.session_id = session_id or str(uuid4())
        self.objective = objective
        self.created_at = created_at or datetime.now()
        self.status = SessionStatus.CREATED
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.paused_at: datetime | None = None
        self.result: Any = None
        self.error: str | None = None
        self.tasks: list[dict[str, Any]] = []
        self.metadata: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        """
        Convert session to dictionary.

        Returns:
            Dict representation
        """
        return {
            "session_id": self.session_id,
            "objective": self.objective,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "tasks": self.tasks,
            "metadata": self.metadata,
            "result": self.result,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        """
        Create session from dictionary.

        Args:
            data: Dict representation

        Returns:
            Session instance
        """
        session = cls(
            session_id=data["session_id"],
            objective=data.get("objective", ""),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
        )

        session.status = SessionStatus(data["status"])

        if data.get("started_at"):
            session.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            session.completed_at = datetime.fromisoformat(data["completed_at"])
        if data.get("paused_at"):
            session.paused_at = datetime.fromisoformat(data["paused_at"])

        session.tasks = data.get("tasks", [])
        session.metadata = data.get("metadata", {})
        session.result = data.get("result")
        session.error = data.get("error")

        return session

    def start(self) -> None:
        """Mark session as started."""
        self.status = SessionStatus.RUNNING
        self.started_at = datetime.now()

    def pause(self) -> None:
        """Pause session execution."""
        if self.status == SessionStatus.RUNNING:
            self.status = SessionStatus.PAUSED
            self.paused_at = datetime.now()

    def resume(self) -> None:
        """Resume paused session."""
        if self.status == SessionStatus.PAUSED:
            self.status = SessionStatus.RUNNING
            self.paused_at = None

    def complete(self, result: Any) -> None:
        """
        Mark session as completed.

        Args:
            result: Execution result
        """
        self.status = SessionStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result

    def fail(self, error: str) -> None:
        """
        Mark session as failed.

        Args:
            error: Error message
        """
        self.status = SessionStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error

    def cancel(self) -> None:
        """Cancel session execution."""
        self.status = SessionStatus.CANCELLED
        self.completed_at = datetime.now()

    def add_task(self, task: dict[str, Any]) -> None:
        """
        Add task to session (dynamic task addition).

        Args:
            task: Task definition
        """
        self.tasks.append(task)


class SessionManager:
    """
    Manages multiple execution sessions.

    Provides session lifecycle management, persistence, and lookup.
    """

    def __init__(self, storage_dir: Path | None = None) -> None:
        """
        Initialize session manager.

        Args:
            storage_dir: Session storage directory (defaults to XDG cache)
        """
        if storage_dir is None:
            storage_dir = get_tessera_cache_dir() / "sessions"

        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._active_sessions: dict[str, Session] = {}
        self._background_tasks: dict[str, asyncio.Task] = {}

        logger.debug(f"SessionManager: {self.storage_dir}")

    def create_session(self, objective: str, metadata: dict[str, Any] | None = None) -> Session:
        """
        Create new session.

        Args:
            objective: Task objective
            metadata: Optional session metadata

        Returns:
            Created session
        """
        session = Session(objective=objective)

        if metadata:
            session.metadata = metadata

        self._active_sessions[session.session_id] = session
        self._save_session(session)

        logger.info(f"Created session {session.session_id}")

        return session

    def get_session(self, session_id: str) -> Session | None:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session or None
        """
        # Check active sessions first
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]

        # Try loading from disk
        return self._load_session(session_id)

    def list_sessions(self, status: SessionStatus | None = None) -> list[Session]:
        """
        List all sessions.

        Args:
            status: Optional status filter

        Returns:
            List of sessions
        """
        sessions = []

        # Get all session files
        for session_file in self.storage_dir.glob("*.json"):
            try:
                session = self._load_session(session_file.stem)
                if session and (status is None or session.status == status):
                    sessions.append(session)
            except Exception as e:
                logger.warning(f"Failed to load session {session_file.stem}: {e}")

        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    def pause_session(self, session_id: str) -> bool:
        """
        Pause a running session.

        Args:
            session_id: Session identifier

        Returns:
            True if paused
        """
        session = self.get_session(session_id)

        if session is None:
            return False

        session.pause()
        self._save_session(session)

        # Cancel background task if running
        if session_id in self._background_tasks:
            self._background_tasks[session_id].cancel()

        logger.info(f"Paused session {session_id}")

        return True

    def resume_session(self, session_id: str) -> bool:
        """
        Resume a paused session.

        Args:
            session_id: Session identifier

        Returns:
            True if resumed
        """
        session = self.get_session(session_id)

        if session is None or session.status != SessionStatus.PAUSED:
            return False

        session.resume()
        self._save_session(session)

        logger.info(f"Resumed session {session_id}")

        return True

    def cancel_session(self, session_id: str) -> bool:
        """
        Cancel a session.

        Args:
            session_id: Session identifier

        Returns:
            True if cancelled
        """
        session = self.get_session(session_id)

        if session is None:
            return False

        session.cancel()
        self._save_session(session)

        # Cancel background task
        if session_id in self._background_tasks:
            self._background_tasks[session_id].cancel()
            del self._background_tasks[session_id]

        logger.info(f"Cancelled session {session_id}")

        return True

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted
        """
        # Remove from active
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]

        # Remove from disk
        session_file = self.storage_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Deleted session {session_id}")
            return True

        return False

    def _save_session(self, session: Session) -> None:
        """Save session to disk."""
        session_file = self.storage_dir / f"{session.session_id}.json"

        try:
            with open(session_file, "w") as f:
                json.dump(session.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")

    def _load_session(self, session_id: str) -> Session | None:
        """Load session from disk."""
        session_file = self.storage_dir / f"{session_id}.json"

        if not session_file.exists():
            return None

        try:
            with open(session_file) as f:
                data = json.load(f)

            session = Session.from_dict(data)
            self._active_sessions[session_id] = session

            return session

        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None


# Global session manager
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """
    Get global session manager instance.

    Returns:
        Global SessionManager
    """
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager()

    return _session_manager
