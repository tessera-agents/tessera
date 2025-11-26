"""
Multi-channel Slack client for agent communication.

Supports:
- Agent-to-agent collaboration channel
- Agent-to-user approval/question channel
- Agent identity management
- Threaded conversations
"""

import ssl
from typing import Any, cast

import certifi
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient

from .agent_identity import AgentIdentityManager


class MultiChannelSlackClient:
    """
    Multi-channel Slack client for Tessera.

    Manages communication across multiple channels with agent identities.
    """

    def __init__(
        self,
        bot_token: str,
        agent_channel: str,
        user_channel: str,
        app_token: str | None = None,
        identity_manager: AgentIdentityManager | None = None,
    ) -> None:
        """
        Initialize multi-channel Slack client.

        All configuration should come from TesseraSettings, not environment variables.

        Args:
            bot_token: Slack bot token (xoxb-...) - REQUIRED
            agent_channel: Channel ID for agent-to-agent - REQUIRED
            user_channel: Channel ID for agent-to-user - REQUIRED
            app_token: Optional app token for Socket Mode (xapp-...)
            identity_manager: Optional custom identity manager
        """
        self.bot_token = bot_token
        self.app_token = app_token
        self.agent_channel = agent_channel
        self.user_channel = user_channel

        if not self.bot_token:
            raise ValueError("SLACK_BOT_TOKEN required")

        # Create SSL context with certifi for certificate verification
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        self.web_client = WebClient(token=self.bot_token, ssl=ssl_context)
        self.socket_client = None
        if self.app_token:
            self.socket_client = SocketModeClient(app_token=self.app_token, web_client=self.web_client)

        self.identity_manager = identity_manager or AgentIdentityManager()

    def post_agent_message(
        self,
        agent_name: str,
        message: str,
        channel: str | None = None,
        thread_ts: str | None = None,
    ) -> dict[str, Any]:
        """
        Post message as an agent to agent collaboration channel.

        Args:
            agent_name: Name of the agent posting
            message: Message text
            channel: Optional channel override (uses agent_channel by default)
            thread_ts: Optional thread timestamp for replies

        Returns:
            Slack API response
        """
        identity = self.identity_manager.get_identity(agent_name)
        channel = channel or self.agent_channel

        if not channel:
            raise ValueError("Agent channel not configured")

        response = self.web_client.chat_postMessage(
            channel=channel,
            text=message,
            username=identity.display_name,
            icon_emoji=identity.emoji,
            thread_ts=thread_ts,
            blocks=[
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"*{identity.display_name}* • {identity.description}",
                        }
                    ],
                },
                {"type": "section", "text": {"type": "mrkdwn", "text": message}},
            ],
        )

        return cast("dict[str, Any]", response.data)

    def post_user_request(
        self,
        agent_name: str,
        message: str,
        request_type: str = "approval",
        metadata: dict[str, Any] | None = None,
        channel: str | None = None,
    ) -> dict[str, Any]:
        """
        Post approval/question request to user channel.

        Args:
            agent_name: Agent requesting approval
            message: Request message
            request_type: Type of request (approval, question, permission)
            metadata: Additional context
            channel: Optional channel override

        Returns:
            Slack API response with message timestamp
        """
        identity = self.identity_manager.get_identity(agent_name)
        channel = channel or self.user_channel

        if not channel:
            raise ValueError("User channel not configured")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{identity.emoji} Agent {request_type.title()} Required",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"From: *{identity.display_name}*",
                    }
                ],
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": message}},
        ]

        # Add metadata if provided
        if metadata:
            metadata_text = "\n".join(f"*{k.replace('_', ' ').title()}:* {v}" for k, v in metadata.items())
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": metadata_text}})

        # Add approval buttons for approval requests
        if request_type == "approval":
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve"},
                            "style": "primary",
                            "value": "approve",
                            "action_id": "approve_action",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Deny"},
                            "style": "danger",
                            "value": "deny",
                            "action_id": "deny_action",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Ask Question"},
                            "value": "question",
                            "action_id": "question_action",
                        },
                    ],
                }
            )

        response = self.web_client.chat_postMessage(channel=channel, text=message, blocks=blocks)
        return cast("dict[str, Any]", response.data)

    def post_status_update(self, agent_name: str, status: str, details: dict[str, Any] | None = None) -> None:
        """
        Post status update to agent channel.

        Args:
            agent_name: Agent name
            status: Status message (e.g., "Task completed", "In progress")
            details: Optional status details
        """
        message = f"*Status:* {status}"
        if details:
            message += "\n" + "\n".join(f"• {k}: {v}" for k, v in details.items())

        self.post_agent_message(agent_name, message)

    def post_user_question(
        self,
        agent_name: str,
        question: str,
        context: str | None = None,
        suggested_answers: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Post question to user channel with optional suggested answers.

        Args:
            agent_name: Agent asking the question
            question: Question text
            context: Optional context about why asking
            suggested_answers: Optional list of suggested answers

        Returns:
            Slack API response
        """
        identity = self.identity_manager.get_identity(agent_name)
        channel = self.user_channel

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{identity.emoji} Agent Question"},
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Question:* {question}"}},
        ]

        if context:
            blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": context}]})

        # Add suggested answers as buttons if provided
        if suggested_answers:
            actions = []
            for i, answer in enumerate(suggested_answers[:5]):  # Max 5 buttons
                actions.append(
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": answer[:75]},  # Max length
                        "value": answer,
                        "action_id": f"answer_{i}",
                    }
                )
            blocks.append({"type": "actions", "elements": actions})

        # Add "Custom Answer" button to allow freeform response
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "💬 Reply in Thread"},
                        "style": "primary",
                        "action_id": "custom_answer",
                    }
                ],
            }
        )

        response = self.web_client.chat_postMessage(channel=channel, text=question, blocks=blocks)
        return cast("dict[str, Any]", response.data)

    def post_clarification_request(
        self,
        agent_name: str,
        requirement: str,
        ambiguity: str,
        options: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Request clarification on ambiguous requirement.

        Args:
            agent_name: Agent requesting clarification
            requirement: The ambiguous requirement
            ambiguity: What's unclear
            options: Optional list of possible interpretations

        Returns:
            Slack API response
        """
        message = f"*Requirement:* {requirement}\n\n*Ambiguity:* {ambiguity}"

        if options:
            message += "\n\n*Possible interpretations:*\n"
            message += "\n".join(f"{i + 1}. {opt}" for i, opt in enumerate(options))

        return self.post_user_question(
            agent_name=agent_name,
            question="Clarification needed",
            context=message,
            suggested_answers=options,
        )
