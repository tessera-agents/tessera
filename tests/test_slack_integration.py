"""
Unit tests for enhanced Slack integration.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from tessera.slack import AgentIdentityManager, MultiChannelSlackClient
from tessera.slack.agent_identity import AgentIdentity


@pytest.mark.unit
class TestAgentIdentityManager:
    """Test agent identity management."""

    def test_emoji_hints_for_python_agent(self):
        """Test emoji selection based on agent name."""
        manager = AgentIdentityManager()

        mock_config = Mock()
        mock_config.name = "python-expert"
        mock_config.capabilities = ["python", "coding"]
        mock_config.system_prompt = "Python coding specialist"

        manager.register_from_config(mock_config)
        identity = manager.get_identity("python-expert")

        assert identity.name == "python-expert"
        assert identity.emoji == ":snake:"
        assert "Python Expert" in identity.display_name

    def test_fallback_emoji_for_unknown_agent(self):
        """Test fallback emoji for agent without hints."""
        manager = AgentIdentityManager()
        identity = manager.get_identity("unknown-agent")

        assert identity.emoji == ":robot_face:"
        assert "Tessera" in identity.display_name

    def test_color_assignment(self):
        """Test colors are assigned to agents."""
        manager = AgentIdentityManager()

        config1 = Mock()
        config1.name = "agent1"
        config1.capabilities = []
        config1.system_prompt = None
        config1.role = None

        config2 = Mock()
        config2.name = "agent2"
        config2.capabilities = []
        config2.system_prompt = None
        config2.role = None

        manager.register_from_config(config1)
        manager.register_from_config(config2)

        identity1 = manager.get_identity("agent1")
        identity2 = manager.get_identity("agent2")

        assert identity1.color != identity2.color  # Different colors


@pytest.mark.unit
class TestMultiChannelSlackClient:
    """Test multi-channel Slack client."""

    @patch('tessera.slack.multi_channel.WebClient')
    def test_initialization(self, mock_webclient):
        """Test client initialization."""
        client = MultiChannelSlackClient(
            bot_token="xoxb-test",
            agent_channel="C123",
            user_channel="C456"
        )

        assert client.bot_token == "xoxb-test"
        assert client.agent_channel == "C123"
        assert client.user_channel == "C456"
        mock_webclient.assert_called_once()

    @patch('tessera.slack.multi_channel.WebClient')
    def test_post_agent_message(self, mock_webclient):
        """Test posting message to agent channel."""
        mock_web = MagicMock()
        mock_webclient.return_value = mock_web

        client = MultiChannelSlackClient(
            bot_token="xoxb-test",
            agent_channel="C123",
            user_channel="C456"
        )

        client.post_agent_message("supervisor", "Test message")

        # Verify chat_postMessage was called
        mock_web.chat_postMessage.assert_called_once()
        call_kwargs = mock_web.chat_postMessage.call_args[1]

        assert call_kwargs["channel"] == "C123"
        assert call_kwargs["text"] == "Test message"
        assert "Tessera" in call_kwargs["username"]

    @patch('tessera.slack.multi_channel.WebClient')
    def test_post_user_question(self, mock_webclient):
        """Test posting question to user channel."""
        mock_web = MagicMock()
        mock_webclient.return_value = mock_web

        client = MultiChannelSlackClient(
            bot_token="xoxb-test",
            agent_channel="C123",
            user_channel="C456"
        )

        client.post_user_question(
            "supervisor",
            "What database?",
            suggested_answers=["PostgreSQL", "MySQL"]
        )

        # Verify posted to user channel
        mock_web.chat_postMessage.assert_called_once()
        call_kwargs = mock_web.chat_postMessage.call_args[1]

        assert call_kwargs["channel"] == "C456"
        assert "What database?" in call_kwargs["text"]
        # Should have buttons for suggested answers
        assert any("PostgreSQL" in str(block) for block in call_kwargs["blocks"])

    @patch('tessera.slack.multi_channel.WebClient')
    def test_post_user_request_approval(self, mock_webclient):
        """Test approval request with buttons."""
        mock_web = MagicMock()
        mock_webclient.return_value = mock_web

        client = MultiChannelSlackClient(
            bot_token="xoxb-test",
            agent_channel="C123",
            user_channel="C456"
        )

        client.post_user_request(
            "python-expert",
            "Deploy to production?",
            request_type="approval",
            metadata={"cost": "$5.00"}
        )

        # Verify approval buttons present
        call_kwargs = mock_web.chat_postMessage.call_args[1]
        blocks = call_kwargs["blocks"]

        # Should have action block with Approve/Deny buttons
        action_blocks = [b for b in blocks if b.get("type") == "actions"]
        assert len(action_blocks) > 0
