"""
LLM provider abstraction using LiteLLM for unified multi-provider support.
"""

from langchain_core.language_models import BaseChatModel
from langchain_litellm import ChatLiteLLM

from .config import LLMConfig


class LLMProvider:
    """Factory for creating LLM instances (backward compatibility wrapper)."""

    @staticmethod
    def create(config: LLMConfig) -> BaseChatModel:
        """Create an LLM instance from configuration."""
        return create_llm(config)


def create_llm(config: LLMConfig | None = None) -> BaseChatModel:
    """
    Create LLM instance using LiteLLM for unified provider support.

    Supports 100+ LLM providers through LiteLLM including:
    - OpenAI (gpt-4, gpt-4o, etc.)
    - Anthropic (claude-3-sonnet, etc.)
    - Azure OpenAI
    - Google (gemini, vertex)
    - Ollama (local models)
    - And many more

    Args:
        config: LLM configuration (provider, model, api_key, etc.)
                If None, loads from environment variables

    Returns:
        BaseChatModel instance configured with LiteLLM

    Example:
        >>> config = LLMConfig.from_env(provider="openai")
        >>> llm = create_llm(config)
        >>> response = llm.invoke("Hello!")
    """
    if config is None:
        config = LLMConfig.from_env()

    # Format model name for LiteLLM
    # LiteLLM expects: "provider/model" format
    # Examples:
    #   - "gpt-4" (OpenAI)
    #   - "anthropic/claude-3-5-sonnet"
    #   - "vertex_ai/claude-3-5-sonnet-v2@20241022"
    #   - "ollama/llama3.2"

    model_name = config.model

    # For non-OpenAI providers, prefix with provider name
    if config.provider not in ("openai"):
        # Special handling for vertex_ai - model might already include provider
        if config.provider == "vertex_ai" and not model_name.startswith("vertex_ai"):
            model_name = f"vertex_ai/{config.model}"
        elif "/" not in model_name:
            model_name = f"{config.provider}/{config.model}"

    # Build kwargs for ChatLiteLLM
    import os # noqa: PLC0415

    llm_kwargs = {
        "model": model_name,
        "api_key": config.api_key,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "timeout": config.timeout,
        "num_retries": config.max_retries,
        "metadata": {
            "project": "tessera",
            "provider": config.provider,
        },
    }

    # Vertex AI specific parameters (must be passed via model_kwargs)
    if config.provider == "vertex_ai":
        vertex_project = os.getenv("VERTEX_PROJECT")
        vertex_location = os.getenv("VERTEX_LOCATION", "us-central1")

        if vertex_project:
            # ChatLiteLLM requires these in model_kwargs, not top-level
            if "model_kwargs" not in llm_kwargs:
                llm_kwargs["model_kwargs"] = {}
            llm_kwargs["model_kwargs"]["vertex_project"] = vertex_project
            llm_kwargs["model_kwargs"]["vertex_location"] = vertex_location

    # Create LiteLLM chat model
    llm = ChatLiteLLM(**llm_kwargs)

    # If base_url is specified (e.g., for local models or proxies)
    if config.base_url:
        llm.model_kwargs["api_base"] = config.base_url

    return llm
