"""Unit tests for Slack approval integration."""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from tessera.slack_approval import SlackApprovalCoordinator, create_slack_client
from tessera.graph_base import get_thread_config, clear_checkpoint_db


@pytest.mark.unit
class TestSlackApprovalCoordinator:
    """Test SlackApprovalCoordinator functionality."""

    def setup_method(self):
        """Clean up checkpoints before each test."""
        clear_checkpoint_db()

    def teardown_method(self):
        """Clean up checkpoints after each test."""
        clear_checkpoint_db()

    def test_coordinator_initialization(self):
        """Test coordinator initialization."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackApprovalCoordinator(
            graph=mock_graph, slack_client=mock_slack_client, default_channel="C12345"
        )

        assert coordinator.graph == mock_graph
        assert coordinator.slack_client == mock_slack_client
        assert coordinator.default_channel == "C12345"
        assert coordinator.pending_interrupts == {}

    def test_coordinator_uses_env_var_for_default_channel(self):
        """Test coordinator reads default channel from environment."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        with patch.dict(os.environ, {"SLACK_APPROVAL_CHANNEL": "C99999"}):
            coordinator = SlackApprovalCoordinator(
                graph=mock_graph, slack_client=mock_slack_client
            )

            assert coordinator.default_channel == "C99999"

    def test_invoke_with_no_interrupt(self):
        """Test invoke when graph doesn't interrupt."""
        mock_graph = Mock()
        mock_graph.invoke = Mock(return_value={"status": "completed"})

        mock_slack_client = Mock()

        coordinator = SlackApprovalCoordinator(
            graph=mock_graph, slack_client=mock_slack_client, default_channel="C12345"
        )

        result = coordinator.invoke_with_slack_approval(
            input_data={"objective": "test"},
            thread_id="test-thread",
            slack_channel="C12345",
        )

        assert result["status"] == "completed"
        assert len(coordinator.pending_interrupts) == 0
        # Slack message should not be sent
        mock_slack_client.web_client.chat_postMessage.assert_not_called()

    def test_invoke_with_interrupt(self):
        """Test invoke when graph interrupts for approval."""
        mock_graph = Mock()
        mock_graph.invoke = Mock(
            return_value={
                "__interrupt__": {
                    "question": "Approve this?",
                    "details": {"action": "delete"},
                },
                "status": "waiting",
            }
        )

        mock_slack_client = Mock()
        mock_slack_client.web_client = Mock()
        mock_slack_client.web_client.chat_postMessage = Mock(
            return_value={"ts": "1234567890.123456"}
        )

        coordinator = SlackApprovalCoordinator(
            graph=mock_graph, slack_client=mock_slack_client, default_channel="C12345"
        )

        result = coordinator.invoke_with_slack_approval(
            input_data={"objective": "test"},
            thread_id="test-thread",
            slack_channel="C12345",
        )

        # Should have pending interrupt
        assert len(coordinator.pending_interrupts) == 1
        assert "1234567890.123456" in coordinator.pending_interrupts

        # Slack message should be sent
        mock_slack_client.web_client.chat_postMessage.assert_called_once()
        call_args = mock_slack_client.web_client.chat_postMessage.call_args
        assert call_args[1]["channel"] == "C12345"
        assert "Approve this?" in call_args[1]["text"]

    def test_invoke_requires_channel(self):
        """Test that invoke raises error if no channel provided."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackApprovalCoordinator(
            graph=mock_graph, slack_client=mock_slack_client
        )

        with pytest.raises(ValueError, match="Slack channel required"):
            coordinator.invoke_with_slack_approval(
                input_data={"objective": "test"}, thread_id="test-thread"
            )

    def test_send_approval_request_formats_message(self):
        """Test approval request message formatting."""
        mock_graph = Mock()
        mock_slack_client = Mock()
        mock_slack_client.web_client = Mock()
        mock_slack_client.web_client.chat_postMessage = Mock(
            return_value={"ts": "1234567890.123456"}
        )

        coordinator = SlackApprovalCoordinator(
            graph=mock_graph, slack_client=mock_slack_client
        )

        interrupt_data = {
            "question": "Approve database migration?",
            "details": {"table": "users", "operation": "add_column"},
        }

        msg_ts = coordinator._send_approval_request(
            channel="C12345", interrupt_data=interrupt_data
        )

        assert msg_ts == "1234567890.123456"

        # Verify message structure
        call_args = mock_slack_client.web_client.chat_postMessage.call_args
        blocks = call_args[1]["blocks"]

        # Should have header
        assert blocks[0]["type"] == "header"
        assert "Agent Approval Required" in blocks[0]["text"]["text"]

        # Should have question
        assert blocks[1]["type"] == "section"
        assert "Approve database migration?" in blocks[1]["text"]["text"]

        # Should have buttons
        actions_block = next(b for b in blocks if b["type"] == "actions")
        assert len(actions_block["elements"]) == 2
        assert actions_block["elements"][0]["action_id"] == "approve_action"
        assert actions_block["elements"][1]["action_id"] == "reject_action"

    def test_handle_approval_response_approve(self):
        """Test handling approval response."""
        mock_graph = Mock()
        mock_graph.invoke = Mock(return_value={"status": "completed"})

        mock_slack_client = Mock()
        mock_slack_client.web_client = Mock()
        mock_slack_client.web_client.chat_update = Mock()

        coordinator = SlackApprovalCoordinator(
            graph=mock_graph, slack_client=mock_slack_client
        )

        # Setup pending interrupt
        coordinator.pending_interrupts["1234567890.123456"] = {
            "thread_id": "test-thread",
            "interrupt_data": {"question": "Approve?"},
            "channel": "C12345",
        }

        result = coordinator.handle_approval_response(
            action_value="approve", message_ts="1234567890.123456"
        )

        assert result["status"] == "completed"

        # Should resume graph with True
        mock_graph.invoke.assert_called_once()

        # Should update Slack message
        mock_slack_client.web_client.chat_update.assert_called_once()
        update_call = mock_slack_client.web_client.chat_update.call_args
        assert "Approved" in update_call[1]["text"]

        # Should remove pending interrupt
        assert len(coordinator.pending_interrupts) == 0

    def test_handle_approval_response_reject(self):
        """Test handling rejection response."""
        mock_graph = Mock()
        mock_graph.invoke = Mock(return_value={"status": "rejected"})

        mock_slack_client = Mock()
        mock_slack_client.web_client = Mock()
        mock_slack_client.web_client.chat_update = Mock()

        coordinator = SlackApprovalCoordinator(
            graph=mock_graph, slack_client=mock_slack_client
        )

        # Setup pending interrupt
        coordinator.pending_interrupts["1234567890.123456"] = {
            "thread_id": "test-thread",
            "interrupt_data": {"question": "Approve?"},
            "channel": "C12345",
        }

        result = coordinator.handle_approval_response(
            action_value="reject", message_ts="1234567890.123456"
        )

        assert result["status"] == "rejected"

        # Should update Slack message
        mock_slack_client.web_client.chat_update.assert_called_once()
        update_call = mock_slack_client.web_client.chat_update.call_args
        assert "Rejected" in update_call[1]["text"]

    def test_handle_approval_response_unknown_message(self):
        """Test handling response for unknown message."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackApprovalCoordinator(
            graph=mock_graph, slack_client=mock_slack_client
        )

        result = coordinator.handle_approval_response(
            action_value="approve", message_ts="unknown"
        )

        assert result is None
        mock_graph.invoke.assert_not_called()

    def test_create_event_handler(self):
        """Test event handler creation."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackApprovalCoordinator(
            graph=mock_graph, slack_client=mock_slack_client
        )

        handler = coordinator.create_event_handler()

        assert callable(handler)

    def test_event_handler_acknowledges_requests(self):
        """Test event handler always acknowledges requests."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackApprovalCoordinator(
            graph=mock_graph, slack_client=mock_slack_client
        )

        handler = coordinator.create_event_handler()

        # Create mock request
        mock_request = Mock()
        mock_request.type = "events_api"
        mock_request.envelope_id = "test-envelope"

        mock_client = Mock()

        # Call handler
        handler(mock_client, mock_request)

        # Should send acknowledgment
        mock_client.send_socket_mode_response.assert_called_once()

    def test_event_handler_processes_button_clicks(self):
        """Test event handler processes button clicks."""
        mock_graph = Mock()
        mock_graph.invoke = Mock(return_value={"status": "completed"})

        mock_slack_client = Mock()
        mock_slack_client.web_client = Mock()
        mock_slack_client.web_client.chat_update = Mock()

        coordinator = SlackApprovalCoordinator(
            graph=mock_graph, slack_client=mock_slack_client
        )

        # Setup pending interrupt
        coordinator.pending_interrupts["1234567890.123456"] = {
            "thread_id": "test-thread",
            "interrupt_data": {"question": "Approve?"},
            "channel": "C12345",
        }

        handler = coordinator.create_event_handler()

        # Create mock interactive request (button click)
        mock_request = Mock()
        mock_request.type = "interactive"
        mock_request.envelope_id = "test-envelope"
        mock_request.payload = {
            "type": "block_actions",
            "message": {"ts": "1234567890.123456"},
            "actions": [{"action_id": "approve_action", "value": "approve"}],
        }

        mock_client = Mock()

        # Call handler
        handler(mock_client, mock_request)

        # Should resume graph
        mock_graph.invoke.assert_called_once()


@pytest.mark.unit
class TestCreateSlackClient:
    """Test create_slack_client utility function."""

    def test_create_client_with_params(self):
        """Test creating client with explicit tokens."""
        with patch("tessera.slack_approval.SocketModeClient") as mock_socket_client:
            with patch("tessera.slack_approval.WebClient") as mock_web_client:
                create_slack_client(
                    app_token="xapp-test", bot_token="xoxb-test"
                )

                mock_web_client.assert_called_once_with(token="xoxb-test")
                mock_socket_client.assert_called_once()

    def test_create_client_with_env_vars(self):
        """Test creating client from environment variables."""
        with patch.dict(
            os.environ,
            {"SLACK_APP_TOKEN": "xapp-env", "SLACK_BOT_TOKEN": "xoxb-env"},
        ):
            with patch("tessera.slack_approval.SocketModeClient") as mock_socket_client:
                with patch("tessera.slack_approval.WebClient") as mock_web_client:
                    create_slack_client()

                    mock_web_client.assert_called_once_with(token="xoxb-env")
                    mock_socket_client.assert_called_once()

    def test_create_client_missing_app_token(self):
        """Test error when app token missing."""
        # Ensure env vars don't interfere
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Slack app token required"):
                create_slack_client(bot_token="xoxb-test")

    def test_create_client_missing_bot_token(self):
        """Test error when bot token missing."""
        # Ensure env vars don't interfere
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Slack bot token required"):
                create_slack_client(app_token="xapp-test")
