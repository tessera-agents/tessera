"""
LangChain callback handlers for capturing LLM metrics.

Extracts token usage, costs, and other metrics from LLM responses.
"""

from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


class TokenUsageCallback(BaseCallbackHandler):
    """
    Callback handler to capture token usage from LLM calls.

    Stores the latest token usage which can be retrieved after execution.
    """

    def __init__(self) -> None:
        """Initialize the callback handler."""
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0
        self.model_name = ""

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """
        Called when LLM finishes.

        Extracts token usage from the response.

        Args:
            response: LLM result containing usage metadata
            **kwargs: Additional arguments
        """
        self.call_count += 1

        # Extract token usage from response
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]

            self.prompt_tokens += usage.get("prompt_tokens", 0)
            self.completion_tokens += usage.get("completion_tokens", 0)
            self.total_tokens += usage.get("total_tokens", 0)

        # Extract model name
        if response.llm_output and "model_name" in response.llm_output:
            self.model_name = response.llm_output["model_name"]

    def get_usage(self) -> dict[str, Any]:
        """
        Get accumulated token usage.

        Returns:
            Dict with token counts and metadata
        """
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "call_count": self.call_count,
            "model_name": self.model_name,
        }

    def reset(self) -> None:
        """Reset all counters."""
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0
        self.model_name = ""
