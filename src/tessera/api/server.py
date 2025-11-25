"""
FastAPI server for Tessera HTTP API.

Provides REST API for remote execution and session management.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ..logging_config import get_logger
from .session import SessionManager, SessionStatus, get_session_manager

logger = get_logger(__name__)


# Request/Response Models
class CreateSessionRequest(BaseModel):
    """Request to create new session."""

    objective: str
    metadata: dict[str, Any] | None = None


class SessionResponse(BaseModel):
    """Session response model."""

    session_id: str
    objective: str
    status: str
    created_at: str
    started_at: str | None
    completed_at: str | None


class TaskAddRequest(BaseModel):
    """Request to add task to session."""

    description: str
    dependencies: list[str] | None = None


def create_app(session_manager: SessionManager | None = None) -> FastAPI:  # noqa: C901
    """
    Create FastAPI application.

    Args:
        session_manager: Optional session manager instance

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="Tessera API",
        description="Multi-agent orchestration HTTP API",
        version="0.4.0",
    )

    manager = session_manager or get_session_manager()

    @app.get("/")
    async def root() -> dict[str, str]:
        """API root endpoint."""
        return {
            "name": "Tessera API",
            "version": "0.4.0",
            "docs": "/docs",
        }

    @app.post("/sessions")
    async def create_session(request: CreateSessionRequest) -> SessionResponse:
        """
        Create new execution session.

        Args:
            request: Session creation request

        Returns:
            Created session
        """
        session = manager.create_session(
            objective=request.objective,
            metadata=request.metadata,
        )

        return SessionResponse(
            session_id=session.session_id,
            objective=session.objective,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
            started_at=None,
            completed_at=None,
        )

    @app.get("/sessions")
    async def list_sessions(status: str | None = None) -> list[SessionResponse]:
        """
        List all sessions.

        Args:
            status: Optional status filter

        Returns:
            List of sessions
        """
        session_status = SessionStatus(status) if status else None
        sessions = manager.list_sessions(status=session_status)

        return [
            SessionResponse(
                session_id=s.session_id,
                objective=s.objective,
                status=s.status.value,
                created_at=s.created_at.isoformat(),
                started_at=s.started_at.isoformat() if s.started_at else None,
                completed_at=s.completed_at.isoformat() if s.completed_at else None,
            )
            for s in sessions
        ]

    @app.get("/sessions/{session_id}")
    async def get_session(session_id: str) -> dict[str, Any]:
        """
        Get session details.

        Args:
            session_id: Session identifier

        Returns:
            Session details
        """
        session = manager.get_session(session_id)

        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        return session.to_dict()

    @app.post("/sessions/{session_id}/pause")
    async def pause_session(session_id: str) -> dict[str, str]:
        """
        Pause running session.

        Args:
            session_id: Session identifier

        Returns:
            Status message
        """
        success = manager.pause_session(session_id)

        if not success:
            raise HTTPException(status_code=400, detail="Cannot pause session")

        return {"status": "paused", "session_id": session_id}

    @app.post("/sessions/{session_id}/resume")
    async def resume_session(session_id: str) -> dict[str, str]:
        """
        Resume paused session.

        Args:
            session_id: Session identifier

        Returns:
            Status message
        """
        success = manager.resume_session(session_id)

        if not success:
            raise HTTPException(status_code=400, detail="Cannot resume session")

        return {"status": "resumed", "session_id": session_id}

    @app.post("/sessions/{session_id}/cancel")
    async def cancel_session(session_id: str) -> dict[str, str]:
        """
        Cancel session.

        Args:
            session_id: Session identifier

        Returns:
            Status message
        """
        success = manager.cancel_session(session_id)

        if not success:
            raise HTTPException(status_code=400, detail="Cannot cancel session")

        return {"status": "cancelled", "session_id": session_id}

    @app.delete("/sessions/{session_id}")
    async def delete_session(session_id: str) -> dict[str, str]:
        """
        Delete session.

        Args:
            session_id: Session identifier

        Returns:
            Status message
        """
        success = manager.delete_session(session_id)

        if not success:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"status": "deleted", "session_id": session_id}

    @app.post("/sessions/{session_id}/tasks")
    async def add_task(session_id: str, request: TaskAddRequest) -> dict[str, str]:
        """
        Add task to session (dynamic task addition).

        Args:
            session_id: Session identifier
            request: Task addition request

        Returns:
            Status message
        """
        session = manager.get_session(session_id)

        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        task = {
            "description": request.description,
            "dependencies": request.dependencies or [],
            "added_at": datetime.now(UTC).isoformat(),
        }

        session.add_task(task)
        manager._save_session(session)

        return {"status": "task_added", "session_id": session_id}

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


def start_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """
    Start Tessera API server.

    Args:
        host: Server host
        port: Server port
    """
    import uvicorn

    app = create_app()

    logger.info(f"Starting Tessera API server on {host}:{port}")

    uvicorn.run(app, host=host, port=port, log_level="info")
