"""
Slack Socket Mode integration for LangGraph approval workflows.

Provides privacy-preserving approval workflows without requiring webhooks.
Uses native Slack SDK with Socket Mode for local, self-hosted operation.
"""

import os
import json
from typing import Dict, Optional, Callable, Any
from slack_sdk.web import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from langgraph.types import Command

from .logging_config import get_logger

logger = get_logger(__name__)

from .graph_base import get_thread_config


class SlackApprovalCoordinator:
    """
    Coordinates LangGraph interrupts with Slack Socket Mode.

    Provides approval workflows using:
    - LangGraph's native interrupt() function
    - Slack Socket Mode (WebSocket-based, no webhooks)
    - Local SQLite state persistence

    Example:
        >>> from slack_sdk.socket_mode import SocketModeClient
        >>> from slack_sdk.web import WebClient
        >>> from tessera.supervisor_graph import SupervisorGraph
        >>>
        >>> # Initialize Slack clients
        >>> slack_client = SocketModeClient(
        >>>     app_token=os.environ["SLACK_APP_TOKEN"],
        >>>     web_client=WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        >>> )
        >>>
        >>> # Initialize coordinator
        >>> supervisor = SupervisorGraph()
        >>> coordinator = SlackApprovalCoordinator(
        >>>     graph=supervisor,
        >>>     slack_client=slack_client
        >>> )
        >>>
        >>> # Register event handler
        >>> slack_client.socket_mode_request_listeners.append(
        >>>     coordinator.create_event_handler()
        >>> )
        >>>
        >>> # Invoke graph with Slack approval
        >>> result = coordinator.invoke_with_slack_approval(
        >>>     input_data={"objective": "Build website"},
        >>>     thread_id="task-123",
        >>>     slack_channel="C12345"
        >>> )
        >>>
        >>> # Connect to Slack
        >>> slack_client.connect()
    """

    def __init__(
        self,
        graph: Any,
        slack_client: SocketModeClient,
        default_channel: Optional[str] = None,
    ):
        """
        Initialize Slack approval coordinator.

        Args:
            graph: LangGraph graph with interrupt nodes
            slack_client: Initialized SocketModeClient
            default_channel: Default Slack channel for approvals
        """
        self.graph = graph
        self.slack_client = slack_client
        self.default_channel = default_channel or os.environ.get(
            "SLACK_APPROVAL_CHANNEL"
        )
        self.pending_interrupts: Dict[str, dict] = {}  # message_ts -> interrupt_data

    def invoke_with_slack_approval(
        self,
        input_data: dict,
        thread_id: str,
        slack_channel: Optional[str] = None,
    ) -> dict:
        """
        Invoke graph with Slack approval handling.

        Args:
            input_data: Graph input state
            thread_id: Unique thread ID for checkpointing
            slack_channel: Slack channel for approval requests

        Returns:
            Final graph state or state with pending interrupt
        """
        channel = slack_channel or self.default_channel
        if not channel:
            raise ValueError(
                "Slack channel required. Provide slack_channel parameter or set SLACK_APPROVAL_CHANNEL env var."
            )

        config = get_thread_config(thread_id)

        # Initial invocation
        result = self.graph.invoke(input_data, config=config)

        # Check for interrupt
        if "__interrupt__" in result:
            interrupt_data = result["__interrupt__"]

            # Send approval request to Slack
            msg_ts = self._send_approval_request(
                channel=channel, interrupt_data=interrupt_data
            )

            # Store pending interrupt
            self.pending_interrupts[msg_ts] = {
                "thread_id": thread_id,
                "interrupt_data": interrupt_data,
                "channel": channel,
            }

        return result

    def _send_approval_request(self, channel: str, interrupt_data: dict) -> str:
        """
        Send approval request to Slack with buttons.

        Args:
            channel: Slack channel ID
            interrupt_data: Interrupt payload from LangGraph

        Returns:
            Message timestamp (ts) for tracking
        """
        question = interrupt_data.get("question", "Approval required")
        details = interrupt_data.get("details", {})

        # Format details for display
        if isinstance(details, dict):
            details_text = "\n".join(
                f"*{k.replace('_', ' ').title()}:* {v}" for k, v in details.items()
            )
        else:
            details_text = str(details)

        response = self.slack_client.web_client.chat_postMessage(
            channel=channel,
            text=question,
            blocks=[
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "🤖 Agent Approval Required"},
                },
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*{question}*"}},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": details_text},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```\n{json.dumps(interrupt_data, indent=2)}\n```",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "✅ Approve"},
                            "style": "primary",
                            "value": "approve",
                            "action_id": "approve_action",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "❌ Reject"},
                            "style": "danger",
                            "value": "reject",
                            "action_id": "reject_action",
                        },
                    ],
                },
            ],
        )

        return response["ts"]

    def handle_approval_response(
        self, action_value: str, message_ts: str
    ) -> Optional[dict]:
        """
        Resume graph after user responds in Slack.

        Args:
            action_value: User's decision ('approve' or 'reject')
            message_ts: Message timestamp identifying the interrupt

        Returns:
            Updated graph state or None if interrupt not found
        """
        if message_ts not in self.pending_interrupts:
            return None

        interrupt_info = self.pending_interrupts.pop(message_ts)
        thread_id = interrupt_info["thread_id"]
        channel = interrupt_info["channel"]
        config = get_thread_config(thread_id)

        # Resume graph with user decision
        approved = action_value == "approve"
        result = self.graph.invoke(Command(resume=approved), config=config)

        # Update Slack message to show decision
        status_text = "✅ Approved" if approved else "❌ Rejected"
        self.slack_client.web_client.chat_update(
            channel=channel,
            ts=message_ts,
            text=status_text,
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{status_text}*"},
                }
            ],
        )

        return result

    def create_event_handler(self) -> Callable[[SocketModeClient, SocketModeRequest], None]:
        """
        Create Socket Mode event handler function.

        Returns:
            Event handler function to register with SocketModeClient
        """

        def handle_socket_mode_request(
            client: SocketModeClient, req: SocketModeRequest
        ):
            """Handle Socket Mode events."""
            # Always acknowledge
            response = SocketModeResponse(envelope_id=req.envelope_id)
            client.send_socket_mode_response(response)

            try:
                # Handle interactive events (button clicks)
                if req.type == "interactive":
                    payload = req.payload

                    if payload["type"] == "block_actions":
                        action = payload["actions"][0]
                        action_id = action["action_id"]

                        if action_id in ["approve_action", "reject_action"]:
                            message_ts = payload["message"]["ts"]
                            action_value = action["value"]

                            # Resume graph
                            self.handle_approval_response(
                                action_value=action_value, message_ts=message_ts
                            )

            except Exception as e:
                logger.error(f"Error processing Slack event: {e}")

        return handle_socket_mode_request


def create_slack_client(
    app_token: Optional[str] = None, bot_token: Optional[str] = None
) -> SocketModeClient:
    """
    Create and configure Slack Socket Mode client.

    Args:
        app_token: Slack app-level token (xapp-...)
        bot_token: Slack bot token (xoxb-...)

    Returns:
        Configured SocketModeClient

    Raises:
        ValueError: If tokens not provided and not in environment
    """
    app_token = app_token or os.environ.get("SLACK_APP_TOKEN")
    bot_token = bot_token or os.environ.get("SLACK_BOT_TOKEN")

    if not app_token:
        raise ValueError(
            "Slack app token required. Set SLACK_APP_TOKEN environment variable or pass app_token parameter."
        )

    if not bot_token:
        raise ValueError(
            "Slack bot token required. Set SLACK_BOT_TOKEN environment variable or pass bot_token parameter."
        )

    web_client = WebClient(token=bot_token)
    socket_client = SocketModeClient(app_token=app_token, web_client=web_client)

    return socket_client
