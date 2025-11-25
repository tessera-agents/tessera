"""Integration tests for Tessera HTTP API server."""

import pytest
from fastapi.testclient import TestClient

from tessera.api.server import create_app
from tessera.api.session import SessionManager, SessionStatus


@pytest.fixture
def mock_session_manager(tmp_path):
    """Create a mock session manager with temp storage."""
    return SessionManager(storage_dir=tmp_path / "sessions")


@pytest.fixture
def api_client(mock_session_manager):
    """Create FastAPI test client with mock session manager."""
    app = create_app(session_manager=mock_session_manager)
    return TestClient(app)


@pytest.mark.integration
class TestAPIRootEndpoint:
    """Test API root endpoint."""

    def test_root_returns_api_info(self, api_client):
        """Test root endpoint returns API information."""
        response = api_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Tessera API"
        assert data["version"] == "0.4.0"
        assert data["docs"] == "/docs"


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_returns_healthy(self, api_client):
        """Test health check endpoint."""
        response = api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.integration
class TestSessionCreation:
    """Test session creation endpoints."""

    def test_create_session_success(self, api_client):
        """Test creating a new session."""
        response = api_client.post(
            "/sessions",
            json={"objective": "Build a web scraper", "metadata": {"project": "test"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["objective"] == "Build a web scraper"
        assert data["status"] == "created"
        assert data["created_at"] is not None
        assert data["started_at"] is None
        assert data["completed_at"] is None

    def test_create_session_minimal(self, api_client):
        """Test creating session with minimal data."""
        response = api_client.post(
            "/sessions",
            json={"objective": "Test task"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["objective"] == "Test task"
        assert data["status"] == "created"


@pytest.mark.integration
class TestSessionList:
    """Test session listing endpoints."""

    def test_list_sessions_empty(self, api_client):
        """Test listing sessions when none exist."""
        response = api_client.get("/sessions")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_sessions_with_sessions(self, api_client, mock_session_manager):
        """Test listing multiple sessions."""
        # Create some sessions
        session1 = mock_session_manager.create_session("Task 1")
        session2 = mock_session_manager.create_session("Task 2")
        session2.start()
        mock_session_manager._save_session(session2)

        response = api_client.get("/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(s["session_id"] == session1.session_id for s in data)
        assert any(s["session_id"] == session2.session_id for s in data)

    def test_list_sessions_filter_by_status(self, api_client, mock_session_manager):
        """Test filtering sessions by status."""
        # Create sessions with different statuses
        session1 = mock_session_manager.create_session("Running task")
        session1.start()
        mock_session_manager._save_session(session1)

        mock_session_manager.create_session("Created task")

        # Filter by running status
        response = api_client.get("/sessions?status=running")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "running"


@pytest.mark.integration
class TestSessionDetails:
    """Test session detail endpoints."""

    def test_get_session_success(self, api_client, mock_session_manager):
        """Test getting session details."""
        session = mock_session_manager.create_session("Test task")

        response = api_client.get(f"/sessions/{session.session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session.session_id
        assert data["objective"] == "Test task"
        assert data["status"] == "created"

    def test_get_session_not_found(self, api_client):
        """Test getting non-existent session."""
        response = api_client.get("/sessions/nonexistent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.integration
class TestSessionControl:
    """Test session control endpoints (pause/resume/cancel)."""

    def test_pause_session_success(self, api_client, mock_session_manager):
        """Test pausing a running session."""
        session = mock_session_manager.create_session("Test task")
        session.start()
        mock_session_manager._save_session(session)

        response = api_client.post(f"/sessions/{session.session_id}/pause")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"
        assert data["session_id"] == session.session_id

        # Verify session was paused
        updated_session = mock_session_manager.get_session(session.session_id)
        assert updated_session.status == SessionStatus.PAUSED

    def test_pause_session_invalid_state(self, api_client, mock_session_manager):
        """Test pausing session in invalid state."""
        session = mock_session_manager.create_session("Test task")
        # Session is in CREATED state, not RUNNING
        # Note: pause() method doesn't raise error, just doesn't change state

        response = api_client.post(f"/sessions/{session.session_id}/pause")

        # Pause returns 200 even if session wasn't running (idempotent)
        assert response.status_code == 200

        # But verify the session state didn't change
        updated_session = mock_session_manager.get_session(session.session_id)
        assert updated_session.status == SessionStatus.CREATED

    def test_resume_session_success(self, api_client, mock_session_manager):
        """Test resuming a paused session."""
        session = mock_session_manager.create_session("Test task")
        session.start()
        session.pause()
        mock_session_manager._save_session(session)

        response = api_client.post(f"/sessions/{session.session_id}/resume")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resumed"

        # Verify session was resumed
        updated_session = mock_session_manager.get_session(session.session_id)
        assert updated_session.status == SessionStatus.RUNNING

    def test_resume_session_invalid_state(self, api_client, mock_session_manager):
        """Test resuming session not in paused state."""
        session = mock_session_manager.create_session("Test task")
        session.start()
        mock_session_manager._save_session(session)

        response = api_client.post(f"/sessions/{session.session_id}/resume")

        assert response.status_code == 400

    def test_cancel_session_success(self, api_client, mock_session_manager):
        """Test cancelling a session."""
        session = mock_session_manager.create_session("Test task")
        session.start()
        mock_session_manager._save_session(session)

        response = api_client.post(f"/sessions/{session.session_id}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

        # Verify session was cancelled
        updated_session = mock_session_manager.get_session(session.session_id)
        assert updated_session.status == SessionStatus.CANCELLED

    def test_cancel_nonexistent_session(self, api_client):
        """Test cancelling non-existent session."""
        response = api_client.post("/sessions/nonexistent-id/cancel")

        assert response.status_code == 400


@pytest.mark.integration
class TestSessionDeletion:
    """Test session deletion endpoint."""

    def test_delete_session_success(self, api_client, mock_session_manager):
        """Test deleting a session."""
        session = mock_session_manager.create_session("Test task")
        session_id = session.session_id

        response = api_client.delete(f"/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["session_id"] == session_id

        # Verify session was deleted
        assert mock_session_manager.get_session(session_id) is None

    def test_delete_nonexistent_session(self, api_client):
        """Test deleting non-existent session."""
        response = api_client.delete("/sessions/nonexistent-id")

        assert response.status_code == 404


@pytest.mark.integration
class TestTaskAddition:
    """Test dynamic task addition to sessions."""

    def test_add_task_success(self, api_client, mock_session_manager):
        """Test adding a task to a session."""
        session = mock_session_manager.create_session("Test task")

        response = api_client.post(
            f"/sessions/{session.session_id}/tasks",
            json={"description": "Subtask 1", "dependencies": []},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "task_added"
        assert data["session_id"] == session.session_id

        # Verify task was added
        updated_session = mock_session_manager.get_session(session.session_id)
        assert len(updated_session.tasks) == 1
        assert updated_session.tasks[0]["description"] == "Subtask 1"

    def test_add_task_with_dependencies(self, api_client, mock_session_manager):
        """Test adding task with dependencies."""
        session = mock_session_manager.create_session("Test task")

        response = api_client.post(
            f"/sessions/{session.session_id}/tasks",
            json={"description": "Subtask 2", "dependencies": ["task-1"]},
        )

        assert response.status_code == 200

        updated_session = mock_session_manager.get_session(session.session_id)
        assert updated_session.tasks[0]["dependencies"] == ["task-1"]

    def test_add_task_to_nonexistent_session(self, api_client):
        """Test adding task to non-existent session."""
        response = api_client.post(
            "/sessions/nonexistent-id/tasks",
            json={"description": "Test task"},
        )

        assert response.status_code == 404


@pytest.mark.integration
class TestAppCreation:
    """Test FastAPI app creation."""

    def test_create_app_with_custom_manager(self, mock_session_manager):
        """Test creating app with custom session manager."""
        app = create_app(session_manager=mock_session_manager)
        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 200

    def test_create_app_without_manager(self):
        """Test creating app without session manager (uses default)."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
