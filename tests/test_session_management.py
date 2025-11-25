"""Tests for session management."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tessera.api.session import Session, SessionManager, SessionStatus


@pytest.mark.unit
class TestSession:
    """Test session functionality."""

    def test_session_creation(self):
        """Test creating a session."""
        session = Session(objective="Test objective")

        assert session.session_id is not None
        assert session.objective == "Test objective"
        assert session.status == SessionStatus.CREATED
        assert session.created_at is not None

    def test_session_lifecycle(self):
        """Test session status transitions."""
        session = Session(objective="Test")

        # Start
        session.start()
        assert session.status == SessionStatus.RUNNING
        assert session.started_at is not None

        # Pause
        session.pause()
        assert session.status == SessionStatus.PAUSED
        assert session.paused_at is not None

        # Resume
        session.resume()
        assert session.status == SessionStatus.RUNNING
        assert session.paused_at is None

        # Complete
        session.complete({"result": "done"})
        assert session.status == SessionStatus.COMPLETED
        assert session.completed_at is not None
        assert session.result == {"result": "done"}

    def test_session_failure(self):
        """Test marking session as failed."""
        session = Session(objective="Test")
        session.start()

        session.fail("Error message")

        assert session.status == SessionStatus.FAILED
        assert session.error == "Error message"
        assert session.completed_at is not None

    def test_session_to_dict(self):
        """Test serializing session to dict."""
        session = Session(objective="Test", session_id="test-123")
        session.start()

        data = session.to_dict()

        assert data["session_id"] == "test-123"
        assert data["objective"] == "Test"
        assert data["status"] == SessionStatus.RUNNING.value
        assert data["started_at"] is not None

    def test_session_from_dict(self):
        """Test deserializing session from dict."""
        data = {
            "session_id": "test-456",
            "objective": "Test obj",
            "status": "running",
            "created_at": datetime.now(UTC).isoformat(),
            "started_at": datetime.now(UTC).isoformat(),
        }

        session = Session.from_dict(data)

        assert session.session_id == "test-456"
        assert session.objective == "Test obj"
        assert session.status == SessionStatus.RUNNING

    def test_add_task(self):
        """Test adding tasks to session."""
        session = Session(objective="Test")

        session.add_task({"description": "Task 1"})
        session.add_task({"description": "Task 2"})

        assert len(session.tasks) == 2


@pytest.mark.unit
class TestSessionManager:
    """Test session manager functionality."""

    def test_create_session(self):
        """Test creating session via manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(Path(tmpdir))

            session = manager.create_session("Build API")

            assert session.objective == "Build API"
            assert session.session_id in manager._active_sessions

            # Check file was created
            session_file = Path(tmpdir) / f"{session.session_id}.json"
            assert session_file.exists()

    def test_get_session(self):
        """Test getting session by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(Path(tmpdir))

            created = manager.create_session("Test")

            # Get from active
            retrieved = manager.get_session(created.session_id)

            assert retrieved is not None
            assert retrieved.session_id == created.session_id

    def test_list_sessions(self):
        """Test listing all sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(Path(tmpdir))

            manager.create_session("Task 1")
            manager.create_session("Task 2")
            manager.create_session("Task 3")

            sessions = manager.list_sessions()

            assert len(sessions) == 3

    def test_list_sessions_by_status(self):
        """Test filtering sessions by status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(Path(tmpdir))

            s1 = manager.create_session("Task 1")
            _ = manager.create_session("Task 2")

            s1.start()
            manager._save_session(s1)

            running_sessions = manager.list_sessions(status=SessionStatus.RUNNING)

            assert len(running_sessions) == 1
            assert running_sessions[0].session_id == s1.session_id

    def test_pause_session(self):
        """Test pausing session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(Path(tmpdir))

            session = manager.create_session("Test")
            session.start()
            manager._save_session(session)

            success = manager.pause_session(session.session_id)

            assert success is True

            # Check status updated
            retrieved = manager.get_session(session.session_id)
            assert retrieved.status == SessionStatus.PAUSED

    def test_resume_session(self):
        """Test resuming session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(Path(tmpdir))

            session = manager.create_session("Test")
            session.start()
            session.pause()
            manager._save_session(session)

            success = manager.resume_session(session.session_id)

            assert success is True

            retrieved = manager.get_session(session.session_id)
            assert retrieved.status == SessionStatus.RUNNING

    def test_cancel_session(self):
        """Test cancelling session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(Path(tmpdir))

            session = manager.create_session("Test")

            success = manager.cancel_session(session.session_id)

            assert success is True

            retrieved = manager.get_session(session.session_id)
            assert retrieved.status == SessionStatus.CANCELLED

    def test_delete_session(self):
        """Test deleting session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(Path(tmpdir))

            session = manager.create_session("Test")
            session_id = session.session_id

            success = manager.delete_session(session_id)

            assert success is True
            assert manager.get_session(session_id) is None

            # File should be deleted
            session_file = Path(tmpdir) / f"{session_id}.json"
            assert not session_file.exists()
