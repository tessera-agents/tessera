"""Extended Slack integration tests for coverage."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from tessera.slack.agent_identity import AgentIdentity, AgentIdentityManager
from tessera.slack.multi_channel import MultiChannelSlackClient


@pytest.mark.unit
class TestAgentIdentityExtended:
    """Extended agent identity tests."""

    def test_agent_identity_creation(self):
        """Test creating agent identity."""
        identity = AgentIdentity(
            name="python-expert",
            display_name="Python Expert",
            emoji=":snake:",
            color="#3776AB",
            description="Python specialist",
        )

        assert identity.name == "python-expert"
        assert identity.display_name == "Python Expert"
        assert identity.emoji == ":snake:"

    def test_identity_manager_with_multiple_agents(self):
        """Test registering multiple agents."""
        manager = AgentIdentityManager()

        config1 = Mock(name="agent1", capabilities=["python"], system_prompt=None, role=None)
        config2 = Mock(name="agent2", capabilities=["testing"], system_prompt=None, role=None)

        manager.register_from_config(config1)
        manager.register_from_config(config2)

        assert len(manager.identities) == 2
        assert "agent1" in manager.identities
        assert "agent2" in manager.identities

    def test_get_identity_creates_default(self):
        """Test getting identity creates default if not registered."""
        manager = AgentIdentityManager()

        identity = manager.get_identity("unknown-agent")

        assert identity.name == "unknown-agent"
        assert identity.emoji == ":robot_face:"
        assert "Tessera" in identity.display_name

    def test_suggest_emoji_for_testing_agent(self):
        """Test emoji suggestion for testing agent."""
        manager = AgentIdentityManager()

        config = Mock(name="test-expert", capabilities=["testing"], system_prompt=None, role=None)
        manager.register_from_config(config)

        identity = manager.get_identity("test-expert")
        assert identity.emoji == ":test_tube:"

    def test_suggest_emoji_for_review_agent(self):
        """Test emoji suggestion for review agent."""
        manager = AgentIdentityManager()

        config = Mock(name="code-reviewer", capabilities=["review"], system_prompt=None, role=None)
        manager.register_from_config(config)

        identity = manager.get_identity("code-reviewer")
        assert identity.emoji == ":mag:"

    def test_extract_description_from_prompt(self):
        """Test extracting description from system prompt."""
        manager = AgentIdentityManager()

        config = Mock(
            name="specialist",
            capabilities=[],
            system_prompt="You are a Python expert specializing in async code.",
            role=None,
        )
        manager.register_from_config(config)

        identity = manager.get_identity("specialist")
        assert "Python expert" in identity.description or "async code" in identity.description


@pytest.mark.unit
class TestMultiChannelSlackExtended:
    """Extended multi-channel Slack tests."""

    @patch("tessera.slack.multi_channel.WebClient")
    def test_post_to_specific_channel(self, mock_webclient):
        """Test posting to specific channel."""
        mock_web = MagicMock()
        mock_webclient.return_value = mock_web

        client = MultiChannelSlackClient(
            bot_token="xoxb-test",
            agent_channel="C123",
            user_channel="C456",
        )

        client.post_agent_message("supervisor", "Test message", channel="C789")

        # Should post to specified channel, not default
        call_kwargs = mock_web.chat_postMessage.call_args[1]
        assert call_kwargs["channel"] == "C789"

    @patch("tessera.slack.multi_channel.WebClient")
    def test_post_with_metadata(self, mock_webclient):
        """Test posting message with metadata."""
        mock_web = MagicMock()
        mock_webclient.return_value = mock_web

        client = MultiChannelSlackClient(
            bot_token="xoxb-test",
            agent_channel="C123",
            user_channel="C456",
        )

        client.post_user_request(
            agent_name="deploy-agent",
            message="Ready to deploy?",
            request_type="approval",
            metadata={"version": "1.0.0", "environment": "production"},
        )

        call_kwargs = mock_web.chat_postMessage.call_args[1]
        blocks = call_kwargs["blocks"]

        # Metadata should be in blocks
        blocks_str = str(blocks)
        assert "version" in blocks_str or "1.0.0" in blocks_str

    @patch("tessera.slack.multi_channel.WebClient")
    def test_post_clarification_request(self, mock_webclient):
        """Test posting clarification request."""
        mock_web = MagicMock()
        mock_webclient.return_value = mock_web

        client = MultiChannelSlackClient(
            bot_token="xoxb-test",
            agent_channel="C123",
            user_channel="C456",
        )

        client.post_clarification_request(
            agent_name="supervisor",
            topic="Database choice",
            reason="Requirements unclear",
            options=["PostgreSQL", "MySQL", "MongoDB"],
        )

        mock_web.chat_postMessage.assert_called_once()
        call_kwargs = mock_web.chat_postMessage.call_args[1]

        assert call_kwargs["channel"] == "C456"  # User channel
        assert "Database choice" in call_kwargs["text"]


@pytest.mark.unit
class TestMetricsStoreExtended:
    """Extended metrics store tests."""

    def test_metrics_store_custom_db_path(self):
        """Test creating metrics store with custom path."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "custom_metrics.db"
            store = MetricsStore(db_path)

            assert store.db_path == db_path

    def test_record_task_lifecycle(self):
        """Test complete task lifecycle in metrics."""
        store = MetricsStore()

        task_id = "lifecycle_task"

        # Record assignment
        store.record_task_assignment(
            task_id=task_id,
            task_description="Complete lifecycle test",
            task_type="implementation",
            agent_name="test-agent",
            agent_config={"model": "gpt-4"},
        )

        # Update to in progress
        store.update_task_status(task_id, "in_progress")

        # Complete
        store.update_task_status(
            task_id,
            "completed",
            result_summary="Task completed successfully",
        )

        # Record performance
        store.record_agent_performance(
            agent_name="test-agent",
            task_id=task_id,
            phase="implementation",
            success=True,
            duration_seconds=30.5,
            cost_usd=0.015,
        )

        # All operations should complete without error
        assert True
