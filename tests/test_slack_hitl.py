"""Unit tests for Slack Human-in-the-Loop integration."""

import os
from unittest.mock import Mock, patch

import pytest

from tessera.graph_base import clear_checkpoint_db
from tessera.slack_hitl import SlackHITLCoordinator, create_slack_client


@pytest.mark.unit
class TestSlackHITLCoordinator:
    """Test SlackHITLCoordinator functionality."""

    def setup_method(self):
        """Clean up checkpoints before each test."""
        clear_checkpoint_db()

    def teardown_method(self):
        """Clean up checkpoints after each test."""
        clear_checkpoint_db()

    def test_coordinator_initialization(self):
        """Test coordinator initialization with explicit channel."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client, default_channel="C12345")

        assert coordinator.graph == mock_graph
        assert coordinator.slack_client == mock_slack_client
        assert coordinator.default_channel == "C12345"
        assert coordinator.pending_interrupts == {}

    def test_coordinator_initialization_no_channel(self):
        """Test coordinator initialization without default channel."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        with patch.dict(os.environ, {}, clear=True):
            coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

            assert coordinator.default_channel is None

    def test_coordinator_uses_env_var_for_default_channel(self):
        """Test coordinator reads default channel from environment."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        with patch.dict(os.environ, {"SLACK_APPROVAL_CHANNEL": "C99999"}):
            coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

            assert coordinator.default_channel == "C99999"

    def test_invoke_with_no_interrupt(self):
        """Test invoke when graph doesn't interrupt."""
        mock_graph = Mock()
        mock_graph.invoke = Mock(return_value={"status": "completed"})

        mock_slack_client = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client, default_channel="C12345")

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
                    "question": "Approve this action?",
                    "details": {"action": "delete_file", "file": "test.txt"},
                },
                "status": "waiting",
            }
        )

        mock_slack_client = Mock()
        mock_slack_client.web_client = Mock()
        mock_slack_client.web_client.chat_postMessage = Mock(return_value={"ts": "1234567890.123456"})

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client, default_channel="C12345")

        result = coordinator.invoke_with_slack_approval(
            input_data={"objective": "test"},
            thread_id="test-thread",
            slack_channel="C12345",
        )

        # Should have pending interrupt
        assert len(coordinator.pending_interrupts) == 1
        assert "1234567890.123456" in coordinator.pending_interrupts

        pending = coordinator.pending_interrupts["1234567890.123456"]
        assert pending["thread_id"] == "test-thread"
        assert pending["channel"] == "C12345"
        assert pending["interrupt_data"]["question"] == "Approve this action?"

        # Slack message should be sent
        mock_slack_client.web_client.chat_postMessage.assert_called_once()
        call_args = mock_slack_client.web_client.chat_postMessage.call_args
        assert call_args[1]["channel"] == "C12345"
        assert "Approve this action?" in call_args[1]["text"]

        # Result should include interrupt
        assert "__interrupt__" in result

    def test_invoke_uses_default_channel(self):
        """Test invoke uses default channel when not specified."""
        mock_graph = Mock()
        mock_graph.invoke = Mock(
            return_value={
                "__interrupt__": {"question": "Approve?", "details": {}},
            }
        )

        mock_slack_client = Mock()
        mock_slack_client.web_client = Mock()
        mock_slack_client.web_client.chat_postMessage = Mock(return_value={"ts": "1234567890.123456"})

        coordinator = SlackHITLCoordinator(
            graph=mock_graph, slack_client=mock_slack_client, default_channel="C_DEFAULT"
        )

        coordinator.invoke_with_slack_approval(
            input_data={"objective": "test"},
            thread_id="test-thread",
        )

        # Should use default channel
        call_args = mock_slack_client.web_client.chat_postMessage.call_args
        assert call_args[1]["channel"] == "C_DEFAULT"

    def test_invoke_requires_channel(self):
        """Test that invoke raises error if no channel provided."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        with pytest.raises(ValueError, match="Slack channel required"):
            coordinator.invoke_with_slack_approval(input_data={"objective": "test"}, thread_id="test-thread")

    def test_send_approval_request_with_dict_details(self):
        """Test approval request message formatting with dict details."""
        mock_graph = Mock()
        mock_slack_client = Mock()
        mock_slack_client.web_client = Mock()
        mock_slack_client.web_client.chat_postMessage = Mock(return_value={"ts": "1234567890.123456"})

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        interrupt_data = {
            "question": "Approve database migration?",
            "details": {"table_name": "users", "operation_type": "add_column", "column": "email"},
        }

        msg_ts = coordinator._send_approval_request(channel="C12345", interrupt_data=interrupt_data)

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

        # Should have formatted details
        assert blocks[2]["type"] == "section"
        details_text = blocks[2]["text"]["text"]
        assert "Table Name:" in details_text
        assert "users" in details_text
        assert "Operation Type:" in details_text
        assert "add_column" in details_text

        # Should have JSON representation
        assert blocks[3]["type"] == "section"
        assert "```" in blocks[3]["text"]["text"]
        assert "table_name" in blocks[3]["text"]["text"]

        # Should have buttons
        actions_block = blocks[4]
        assert actions_block["type"] == "actions"
        assert len(actions_block["elements"]) == 2
        assert actions_block["elements"][0]["action_id"] == "approve_action"
        assert actions_block["elements"][0]["value"] == "approve"
        assert actions_block["elements"][0]["style"] == "primary"
        assert actions_block["elements"][1]["action_id"] == "reject_action"
        assert actions_block["elements"][1]["value"] == "reject"
        assert actions_block["elements"][1]["style"] == "danger"

    def test_send_approval_request_with_string_details(self):
        """Test approval request with non-dict details."""
        mock_graph = Mock()
        mock_slack_client = Mock()
        mock_slack_client.web_client = Mock()
        mock_slack_client.web_client.chat_postMessage = Mock(return_value={"ts": "1234567890.123456"})

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        interrupt_data = {
            "question": "Continue?",
            "details": "This is a string detail",
        }

        coordinator._send_approval_request(channel="C12345", interrupt_data=interrupt_data)

        # Verify details formatting
        call_args = mock_slack_client.web_client.chat_postMessage.call_args
        blocks = call_args[1]["blocks"]
        details_text = blocks[2]["text"]["text"]
        assert details_text == "This is a string detail"

    def test_send_approval_request_default_question(self):
        """Test approval request with missing question field."""
        mock_graph = Mock()
        mock_slack_client = Mock()
        mock_slack_client.web_client.chat_postMessage = Mock(return_value={"ts": "1234567890.123456"})

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        interrupt_data = {"details": {}}

        coordinator._send_approval_request(channel="C12345", interrupt_data=interrupt_data)

        # Should use default question
        call_args = mock_slack_client.web_client.chat_postMessage.call_args
        assert "Approval required" in call_args[1]["text"]

    def test_send_approval_request_empty_details(self):
        """Test approval request with empty details."""
        mock_graph = Mock()
        mock_slack_client = Mock()
        mock_slack_client.web_client.chat_postMessage = Mock(return_value={"ts": "1234567890.123456"})

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        interrupt_data = {"question": "Test?", "details": {}}

        coordinator._send_approval_request(channel="C12345", interrupt_data=interrupt_data)

        call_args = mock_slack_client.web_client.chat_postMessage.call_args
        blocks = call_args[1]["blocks"]
        # Empty details should result in empty string
        assert blocks[2]["text"]["text"] == ""

    def test_send_approval_request_returns_empty_string_on_missing_ts(self):
        """Test approval request handles missing timestamp."""
        mock_graph = Mock()
        mock_slack_client = Mock()
        mock_slack_client.web_client.chat_postMessage = Mock(return_value={})

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        msg_ts = coordinator._send_approval_request(channel="C12345", interrupt_data={})

        assert msg_ts == ""

    def test_handle_approval_response_approve(self):
        """Test handling approval response."""
        mock_graph = Mock()
        mock_graph.invoke = Mock(return_value={"status": "completed"})

        mock_slack_client = Mock()
        mock_slack_client.web_client = Mock()
        mock_slack_client.web_client.chat_update = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        # Setup pending interrupt
        coordinator.pending_interrupts["1234567890.123456"] = {
            "thread_id": "test-thread",
            "interrupt_data": {"question": "Approve?"},
            "channel": "C12345",
        }

        result = coordinator.handle_approval_response(action_value="approve", message_ts="1234567890.123456")

        assert result["status"] == "completed"

        # Should resume graph with Command(resume=True)
        mock_graph.invoke.assert_called_once()
        call_args = mock_graph.invoke.call_args
        command = call_args[0][0]
        assert command.resume is True

        # Should update Slack message
        mock_slack_client.web_client.chat_update.assert_called_once()
        update_call = mock_slack_client.web_client.chat_update.call_args
        assert update_call[1]["channel"] == "C12345"
        assert update_call[1]["ts"] == "1234567890.123456"
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

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        # Setup pending interrupt
        coordinator.pending_interrupts["1234567890.123456"] = {
            "thread_id": "test-thread",
            "interrupt_data": {"question": "Approve?"},
            "channel": "C12345",
        }

        result = coordinator.handle_approval_response(action_value="reject", message_ts="1234567890.123456")

        assert result["status"] == "rejected"

        # Should resume graph with Command(resume=False)
        call_args = mock_graph.invoke.call_args
        command = call_args[0][0]
        assert command.resume is False

        # Should update Slack message
        mock_slack_client.web_client.chat_update.assert_called_once()
        update_call = mock_slack_client.web_client.chat_update.call_args
        assert "Rejected" in update_call[1]["text"]

    def test_handle_approval_response_unknown_message(self):
        """Test handling response for unknown message."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        result = coordinator.handle_approval_response(action_value="approve", message_ts="unknown")

        assert result is None
        mock_graph.invoke.assert_not_called()

    def test_create_event_handler(self):
        """Test event handler creation."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        handler = coordinator.create_event_handler()

        assert callable(handler)

    def test_event_handler_acknowledges_all_requests(self):
        """Test event handler always acknowledges requests."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        handler = coordinator.create_event_handler()

        # Create mock request
        mock_request = Mock()
        mock_request.type = "events_api"
        mock_request.envelope_id = "test-envelope-123"

        mock_client = Mock()

        # Call handler
        handler(mock_client, mock_request)

        # Should send acknowledgment
        mock_client.send_socket_mode_response.assert_called_once()
        response = mock_client.send_socket_mode_response.call_args[0][0]
        assert response.envelope_id == "test-envelope-123"

    def test_event_handler_processes_approve_action(self):
        """Test event handler processes approve button clicks."""
        mock_graph = Mock()
        mock_graph.invoke = Mock(return_value={"status": "completed"})

        mock_slack_client = Mock()
        mock_slack_client.web_client = Mock()
        mock_slack_client.web_client.chat_update = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        # Setup pending interrupt
        coordinator.pending_interrupts["1234567890.123456"] = {
            "thread_id": "test-thread",
            "interrupt_data": {"question": "Approve?"},
            "channel": "C12345",
        }

        handler = coordinator.create_event_handler()

        # Create mock interactive request (approve button click)
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

        # Should acknowledge
        mock_client.send_socket_mode_response.assert_called_once()

        # Should resume graph
        mock_graph.invoke.assert_called_once()

    def test_event_handler_processes_reject_action(self):
        """Test event handler processes reject button clicks."""
        mock_graph = Mock()
        mock_graph.invoke = Mock(return_value={"status": "rejected"})

        mock_slack_client = Mock()
        mock_slack_client.web_client = Mock()
        mock_slack_client.web_client.chat_update = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        # Setup pending interrupt
        coordinator.pending_interrupts["1234567890.123456"] = {
            "thread_id": "test-thread",
            "interrupt_data": {"question": "Approve?"},
            "channel": "C12345",
        }

        handler = coordinator.create_event_handler()

        # Create mock interactive request (reject button click)
        mock_request = Mock()
        mock_request.type = "interactive"
        mock_request.envelope_id = "test-envelope"
        mock_request.payload = {
            "type": "block_actions",
            "message": {"ts": "1234567890.123456"},
            "actions": [{"action_id": "reject_action", "value": "reject"}],
        }

        mock_client = Mock()

        # Call handler
        handler(mock_client, mock_request)

        # Should resume graph
        mock_graph.invoke.assert_called_once()

    def test_event_handler_ignores_non_interactive_events(self):
        """Test event handler ignores non-interactive events."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        handler = coordinator.create_event_handler()

        # Create mock non-interactive request
        mock_request = Mock()
        mock_request.type = "events_api"
        mock_request.envelope_id = "test-envelope"

        mock_client = Mock()

        # Call handler
        handler(mock_client, mock_request)

        # Should acknowledge but not process
        mock_client.send_socket_mode_response.assert_called_once()
        mock_graph.invoke.assert_not_called()

    def test_event_handler_ignores_non_block_actions(self):
        """Test event handler ignores non-block_actions interactive events."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        handler = coordinator.create_event_handler()

        # Create mock interactive request with wrong type
        mock_request = Mock()
        mock_request.type = "interactive"
        mock_request.envelope_id = "test-envelope"
        mock_request.payload = {"type": "view_submission"}

        mock_client = Mock()

        # Call handler
        handler(mock_client, mock_request)

        # Should acknowledge but not process
        mock_client.send_socket_mode_response.assert_called_once()
        mock_graph.invoke.assert_not_called()

    def test_event_handler_ignores_unknown_action_ids(self):
        """Test event handler ignores unknown action IDs."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        handler = coordinator.create_event_handler()

        # Create mock interactive request with unknown action
        mock_request = Mock()
        mock_request.type = "interactive"
        mock_request.envelope_id = "test-envelope"
        mock_request.payload = {
            "type": "block_actions",
            "message": {"ts": "1234567890.123456"},
            "actions": [{"action_id": "unknown_action", "value": "unknown"}],
        }

        mock_client = Mock()

        # Call handler
        handler(mock_client, mock_request)

        # Should acknowledge but not process
        mock_client.send_socket_mode_response.assert_called_once()
        mock_graph.invoke.assert_not_called()

    def test_event_handler_handles_value_error(self):
        """Test event handler handles ValueError gracefully."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)
        coordinator.handle_approval_response = Mock(side_effect=ValueError("Test error"))

        handler = coordinator.create_event_handler()

        # Create mock request that would trigger error
        mock_request = Mock()
        mock_request.type = "interactive"
        mock_request.envelope_id = "test-envelope"
        mock_request.payload = {
            "type": "block_actions",
            "message": {"ts": "1234567890.123456"},
            "actions": [{"action_id": "approve_action", "value": "approve"}],
        }

        mock_client = Mock()

        # Should not raise exception
        handler(mock_client, mock_request)

        # Should still acknowledge
        mock_client.send_socket_mode_response.assert_called_once()

    def test_event_handler_handles_key_error(self):
        """Test event handler handles KeyError gracefully."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)

        handler = coordinator.create_event_handler()

        # Create mock request with missing keys
        mock_request = Mock()
        mock_request.type = "interactive"
        mock_request.envelope_id = "test-envelope"
        mock_request.payload = {"type": "block_actions"}  # Missing message/actions

        mock_client = Mock()

        # Should not raise exception
        handler(mock_client, mock_request)

        # Should still acknowledge
        mock_client.send_socket_mode_response.assert_called_once()

    def test_event_handler_handles_runtime_error(self):
        """Test event handler handles RuntimeError gracefully."""
        mock_graph = Mock()
        mock_slack_client = Mock()

        coordinator = SlackHITLCoordinator(graph=mock_graph, slack_client=mock_slack_client)
        coordinator.handle_approval_response = Mock(side_effect=RuntimeError("Test error"))

        handler = coordinator.create_event_handler()

        # Create mock request
        mock_request = Mock()
        mock_request.type = "interactive"
        mock_request.envelope_id = "test-envelope"
        mock_request.payload = {
            "type": "block_actions",
            "message": {"ts": "1234567890.123456"},
            "actions": [{"action_id": "approve_action", "value": "approve"}],
        }

        mock_client = Mock()

        # Should not raise exception
        handler(mock_client, mock_request)

        # Should still acknowledge
        mock_client.send_socket_mode_response.assert_called_once()


@pytest.mark.unit
class TestCreateSlackClient:
    """Test create_slack_client utility function."""

    def test_create_client_with_params(self):
        """Test creating client with explicit tokens."""
        with patch("tessera.slack_hitl.SocketModeClient") as mock_socket_client:
            with patch("tessera.slack_hitl.WebClient") as mock_web_client:
                create_slack_client(app_token="xapp-test", bot_token="xoxb-test")

                mock_web_client.assert_called_once_with(token="xoxb-test")
                mock_socket_client.assert_called_once()

    def test_create_client_with_env_vars(self):
        """Test creating client from environment variables."""
        with (
            patch.dict(
                os.environ,
                {"SLACK_APP_TOKEN": "xapp-env", "SLACK_BOT_TOKEN": "xoxb-env"},
            ),
            patch("tessera.slack_hitl.SocketModeClient") as mock_socket_client,
            patch("tessera.slack_hitl.WebClient") as mock_web_client,
        ):
            create_slack_client()

            mock_web_client.assert_called_once_with(token="xoxb-env")
            mock_socket_client.assert_called_once()

    def test_create_client_missing_app_token(self):
        """Test error when app token missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Slack app token required"):
                create_slack_client(bot_token="xoxb-test")

    def test_create_client_missing_bot_token(self):
        """Test error when bot token missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Slack bot token required"):
                create_slack_client(app_token="xapp-test")

    def test_create_client_app_token_from_env(self):
        """Test creating client with app token from env, bot token from param."""
        with patch.dict(os.environ, {"SLACK_APP_TOKEN": "xapp-env"}):
            with patch("tessera.slack_hitl.SocketModeClient") as mock_socket_client:
                with patch("tessera.slack_hitl.WebClient") as mock_web_client:
                    create_slack_client(bot_token="xoxb-param")

                    mock_web_client.assert_called_once_with(token="xoxb-param")
                    mock_socket_client.assert_called_once()
                    # Verify app_token was passed from env
                    call_args = mock_socket_client.call_args
                    assert call_args[1]["app_token"] == "xapp-env"

    def test_create_client_bot_token_from_env(self):
        """Test creating client with bot token from env, app token from param."""
        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-env"}):
            with patch("tessera.slack_hitl.SocketModeClient") as mock_socket_client:
                with patch("tessera.slack_hitl.WebClient") as mock_web_client:
                    create_slack_client(app_token="xapp-param")

                    mock_web_client.assert_called_once_with(token="xoxb-env")
                    mock_socket_client.assert_called_once()
