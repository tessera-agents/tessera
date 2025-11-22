"""
Tests for LLM provider abstraction.
"""

import pytest
from unittest.mock import Mock, patch

from tessera.llm import create_llm, LLMProvider
from tessera.legacy_config import LLMConfig


@pytest.mark.unit
class TestCreateLLM:
    """Test create_llm function."""

    @patch("tessera.llm.ChatLiteLLM")
    def test_create_llm_openai(self, mock_litellm):
        """Test creating OpenAI LLM."""
        config = LLMConfig(
            provider="openai",
            models=["gpt-4"],
            api_key="test-key",
            temperature=0.7
        )

        llm = create_llm(config)

        mock_litellm.assert_called_once()
        call_kwargs = mock_litellm.call_args[1]
        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["temperature"] == 0.7

    @patch("tessera.llm.ChatLiteLLM")
    def test_create_llm_anthropic(self, mock_litellm):
        """Test creating Anthropic LLM via Vertex."""
        config = LLMConfig(
            provider="anthropic",
            models=["claude-3-sonnet"],
            api_key="test-key"
        )

        llm = create_llm(config)

        # Anthropic models get provider prefix
        call_kwargs = mock_litellm.call_args[1]
        assert "anthropic/" in call_kwargs["model"]

    @patch("tessera.llm.ChatLiteLLM")
    def test_create_llm_vertex_ai(self, mock_litellm):
        """Test creating Vertex AI LLM."""
        import os
        os.environ["VERTEX_PROJECT"] = "test-project"
        os.environ["VERTEX_LOCATION"] = "us-east5"

        config = LLMConfig(
            provider="vertex_ai",
            models=["claude-sonnet-4"],
            api_key="not-used"
        )

        llm = create_llm(config)

        # Vertex AI should have model_kwargs with project/location
        call_kwargs = mock_litellm.call_args[1]
        assert "vertex_ai/" in call_kwargs["model"]
        assert "model_kwargs" in call_kwargs
        assert call_kwargs["model_kwargs"]["vertex_project"] == "test-project"
        assert call_kwargs["model_kwargs"]["vertex_location"] == "us-east5"

        # Cleanup
        del os.environ["VERTEX_PROJECT"]
        del os.environ["VERTEX_LOCATION"]

    @patch("tessera.llm.ChatLiteLLM")
    def test_create_llm_with_base_url(self, mock_litellm):
        """Test LLM with custom base URL."""
        mock_instance = Mock()
        mock_instance.model_kwargs = {}
        mock_litellm.return_value = mock_instance

        config = LLMConfig(
            provider="openai",
            models=["gpt-4"],
            api_key="test-key",
            base_url="http://localhost:4141/v1"
        )

        llm = create_llm(config)

        # base_url should be set in model_kwargs
        assert llm.model_kwargs["api_base"] == "http://localhost:4141/v1"

    @patch("tessera.llm.ChatLiteLLM")
    def test_create_llm_metadata(self, mock_litellm):
        """Test LLM includes metadata."""
        config = LLMConfig(
            provider="openai",
            models=["gpt-4"],
            api_key="test-key"
        )

        llm = create_llm(config)

        call_kwargs = mock_litellm.call_args[1]
        assert "metadata" in call_kwargs
        assert call_kwargs["metadata"]["project"] == "tessera"
        assert call_kwargs["metadata"]["provider"] == "openai"


@pytest.mark.unit
class TestLLMProvider:
    """Test LLMProvider factory."""

    @patch("tessera.llm.create_llm")
    def test_llm_provider_create(self, mock_create_llm):
        """Test LLMProvider.create calls create_llm."""
        config = LLMConfig(
            provider="openai",
            models=["gpt-4"],
            api_key="test"
        )

        LLMProvider.create(config)

        mock_create_llm.assert_called_once_with(config)
