"""Unit tests for configuration and LLM providers."""

import pytest
import os
from unittest.mock import patch, Mock
from tessera.config import (
    LLMConfig,
    ScoringWeights,
    FrameworkConfig,
    SUPERVISOR_PROMPT,
    INTERVIEWER_PROMPT,
)
from tessera.llm import LLMProvider, create_llm


@pytest.mark.unit
class TestLLMConfig:
    """Test LLM configuration."""

    def test_llm_config_creation(self):
        """Test creating LLM config."""
        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=["gpt-4"],
            temperature=0.7,
        )

        assert config.provider == "openai"
        assert config.api_key == "test-key"
        assert config.model == "gpt-4"
        assert config.temperature == 0.7

    def test_llm_config_anthropic(self):
        """Test Anthropic config."""
        config = LLMConfig(
            provider="anthropic",
            api_key="test-key",
            models=["claude-3-5-sonnet-20241022"],
        )

        assert config.provider == "anthropic"
        assert config.model == "claude-3-5-sonnet-20241022"

    def test_llm_config_azure(self):
        """Test Azure config."""
        config = LLMConfig(
            provider="azure",
            api_key="test-key",
            models=["gpt-4"],
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="test-deployment",
        )

        assert config.provider == "azure"
        assert config.azure_endpoint == "https://test.openai.azure.com"
        assert config.azure_deployment == "test-deployment"

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-openai-key",
        "OPENAI_MODEL": "gpt-4-turbo",
        "DEFAULT_TEMPERATURE": "0.8",
    }, clear=True)
    @patch("tessera.secrets.SecretManager.get_from_1password")
    def test_llm_config_from_env_openai(self, mock_1password):
        """Test creating config from environment for OpenAI."""
        # Prevent 1Password CLI access (env vars will still work)
        mock_1password.return_value = None

        config = LLMConfig.from_env("openai")

        assert config.provider == "openai"
        assert config.api_key == "test-openai-key"
        assert config.model == "gpt-4-turbo"
        assert config.temperature == 0.8

    @patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "ANTHROPIC_MODEL": "claude-3-opus",
    }, clear=True)
    @patch("tessera.secrets.SecretManager.get_from_1password")
    def test_llm_config_from_env_anthropic(self, mock_1password):
        """Test creating config from environment for Anthropic."""
        # Prevent 1Password CLI access (env vars will still work)
        mock_1password.return_value = None

        config = LLMConfig.from_env("anthropic")

        assert config.provider == "anthropic"
        assert config.api_key == "test-anthropic-key"
        assert config.model == "claude-3-opus"

    def test_llm_config_from_env_invalid_provider(self):
        """Test invalid provider raises error."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            LLMConfig.from_env("invalid_provider")

    def test_llm_config_no_models_raises_error(self):
        """Test that accessing .model with no models configured raises informative error."""
        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=[],  # Empty models list
        )

        with pytest.raises(ValueError, match="No models configured"):
            _ = config.model

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    @patch("tessera.secrets.SecretManager.get_from_1password")
    def test_llm_config_from_env_no_models_creates_empty_list(self, mock_1password):
        """Test that from_env with no model configuration creates empty models list."""
        # Prevent 1Password CLI access (env vars will still work)
        mock_1password.return_value = None

        config = LLMConfig.from_env("openai")

        assert config.models == []
        # Accessing .model should raise error
        with pytest.raises(ValueError, match="No models configured"):
            _ = config.model

    @patch("tessera.model_validator.ModelValidator.fetch_available_models")
    def test_llm_config_no_models_with_proxy_fetches_and_exits(self, mock_fetch):
        """Test that accessing .model with no models and base_url fetches available models and exits."""
        mock_fetch.return_value = ["gpt-4", "gpt-3.5-turbo", "o1-preview"]

        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=[],
            base_url="http://localhost:3000/v1",
        )

        # Should call sys.exit(1) after fetching and displaying models
        with pytest.raises(SystemExit) as exc_info:
            _ = config.model

        assert exc_info.value.code == 1
        mock_fetch.assert_called_once_with("http://localhost:3000/v1", "test-key")

    @patch("tessera.model_validator.ModelValidator.fetch_available_models")
    def test_llm_config_no_models_with_proxy_fetch_fails_still_exits(self, mock_fetch):
        """Test that accessing .model with base_url still exits even if fetch fails."""
        mock_fetch.return_value = None  # Simulate fetch failure

        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=[],
            base_url="http://localhost:3000/v1",
        )

        # Should still call sys.exit(1)
        with pytest.raises(SystemExit) as exc_info:
            _ = config.model

        assert exc_info.value.code == 1
        mock_fetch.assert_called_once_with("http://localhost:3000/v1", "test-key")


@pytest.mark.unit
class TestScoringWeights:
    """Test scoring weights."""

    def test_scoring_weights_defaults(self):
        """Test default scoring weights."""
        weights = ScoringWeights()

        assert weights.accuracy == 0.30
        assert weights.relevance == 0.20
        assert weights.completeness == 0.15
        assert weights.explainability == 0.10
        assert weights.efficiency == 0.10
        assert weights.safety == 0.15

    def test_scoring_weights_custom(self):
        """Test custom scoring weights."""
        weights = ScoringWeights(
            accuracy=0.5,
            relevance=0.2,
            completeness=0.1,
            explainability=0.1,
            efficiency=0.05,
            safety=0.05,
        )

        assert weights.accuracy == 0.5
        assert weights.safety == 0.05

    def test_scoring_weights_normalize(self):
        """Test normalizing scoring weights."""
        weights = ScoringWeights(
            accuracy=2.0,
            relevance=1.0,
            completeness=1.0,
            explainability=1.0,
            efficiency=1.0,
            safety=1.0,
        )

        normalized = weights.normalize()
        total = (
            normalized.accuracy
            + normalized.relevance
            + normalized.completeness
            + normalized.explainability
            + normalized.efficiency
            + normalized.safety
        )

        assert abs(total - 1.0) < 0.001  # Should sum to 1.0

    def test_scoring_weights_normalize_zero_total(self):
        """Test normalizing when all weights are zero."""
        weights = ScoringWeights(
            accuracy=0.0,
            relevance=0.0,
            completeness=0.0,
            explainability=0.0,
            efficiency=0.0,
            safety=0.0,
        )

        normalized = weights.normalize()
        assert normalized.accuracy == 0.0


@pytest.mark.unit
class TestFrameworkConfig:
    """Test framework configuration."""

    def test_framework_config_creation(self, test_config):
        """Test creating framework config."""
        assert test_config.llm.provider == "openai"
        assert test_config.max_iterations == 10
        assert test_config.enable_logging is False

    def test_framework_config_with_custom_weights(self):
        """Test framework config with custom scoring weights."""
        weights = ScoringWeights(accuracy=0.5, safety=0.5)
        config = FrameworkConfig(scoring_weights=weights)

        assert config.scoring_weights.accuracy == 0.5
        assert config.scoring_weights.safety == 0.5

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "MAX_ITERATIONS": "20",
        "ENABLE_LOGGING": "false",
    })
    def test_framework_config_from_env(self):
        """Test creating framework config from environment."""
        config = FrameworkConfig.from_env()

        assert config.max_iterations == 20
        assert config.enable_logging is False


@pytest.mark.unit
class TestPrompts:
    """Test default prompts."""

    def test_supervisor_prompt_exists(self):
        """Test supervisor prompt is defined."""
        assert len(SUPERVISOR_PROMPT) > 0
        assert "Supervisor" in SUPERVISOR_PROMPT
        assert "RESPONSIBILITIES" in SUPERVISOR_PROMPT

    def test_interviewer_prompt_exists(self):
        """Test interviewer prompt is defined."""
        assert len(INTERVIEWER_PROMPT) > 0
        assert "Interviewer" in INTERVIEWER_PROMPT
        assert "INTERVIEW METHODOLOGY" in INTERVIEWER_PROMPT


@pytest.mark.unit
class TestLLMProvider:
    """Test LLM provider factory."""

    @pytest.fixture(autouse=False)  # Disable the global mock for this class
    def mock_llm_creation(self):
        pass

    @patch("tessera.llm.ChatLiteLLM")
    def test_create_openai_llm(self, mock_chat_litellm):
        """Test creating OpenAI LLM."""
        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=["gpt-4"],
            temperature=0.7,
        )

        LLMProvider.create(config)

        mock_chat_litellm.assert_called_once()
    @patch("tessera.llm.ChatLiteLLM")
    def test_create_anthropic_llm(self, mock_chat_litellm):
        """Test creating Anthropic LLM."""
        config = LLMConfig(
            provider="anthropic",
            api_key="test-key",
            models=["claude-3-5-sonnet-20241022"],
            temperature=0.5,
        )

        LLMProvider.create(config)

        mock_chat_litellm.assert_called_once()
    @patch("tessera.llm.ChatLiteLLM")
    def test_create_azure_llm(self, mock_chat_litellm):
        """Test creating Azure OpenAI LLM."""
        config = LLMConfig(
            provider="azure",
            api_key="test-key",
            models=["gpt-4"],
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="test-deployment",
            temperature=0.6,
        )

        LLMProvider.create(config)

        mock_chat_litellm.assert_called_once()

    def test_create_invalid_provider(self):
        """Test creating LLM with invalid provider."""
        # Pydantic validates provider type, so this should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            config = LLMConfig(
                provider="invalid",  # type: ignore
                api_key="test-key",
                models=["test-model"],
            )

    @patch("tessera.llm.ChatLiteLLM")
    def test_create_openai_with_timeout(self, mock_chat_litellm):
        """Test creating OpenAI LLM with timeout."""
        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=["gpt-4"],
            temperature=0.7,
            timeout=60.0,
        )

        LLMProvider.create(config)

        mock_chat_litellm.assert_called_once()

    @patch("tessera.llm.ChatLiteLLM")
    def test_create_openai_with_base_url(self, mock_chat_litellm):
        """Test creating OpenAI LLM with base_url for Copilot proxy."""
        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=["gpt-4"],
            temperature=0.7,
            base_url="http://localhost:3000/v1",
        )

        LLMProvider.create(config)

        mock_chat_litellm.assert_called_once()

    @patch("tessera.llm.ChatLiteLLM")
    def test_create_anthropic_with_timeout(self, mock_chat_litellm):
        """Test creating Anthropic LLM with timeout."""
        config = LLMConfig(
            provider="anthropic",
            api_key="test-key",
            models=["claude-3-5-sonnet-20241022"],
            temperature=0.5,
            timeout=90.0,
        )

        LLMProvider.create(config)

        mock_chat_litellm.assert_called_once()

    @patch("tessera.llm.ChatLiteLLM")
    def test_create_azure_with_timeout(self, mock_chat_litellm):
        """Test creating Azure LLM with timeout."""
        config = LLMConfig(
            provider="azure",
            api_key="test-key",
            models=["gpt-4"],
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="test-deployment",
            temperature=0.6,
            timeout=120.0,
        )

        LLMProvider.create(config)

        call_kwargs = mock_chat_litellm.call_args[1]
        assert call_kwargs["timeout"] == 120.0

    @patch("tessera.llm.LLMConfig.from_env")
    @patch("tessera.llm.LLMProvider.create")
    def test_create_llm_convenience_function(self, mock_create, mock_from_env):
        """Test create_llm with config."""
        config = LLMConfig(provider="openai", models=["gpt-4"], api_key="test")
        llm = create_llm(config)
        assert llm is not None

    @patch("tessera.llm.LLMConfig.from_env")
    @patch("tessera.llm.LLMProvider.create")
    def test_create_llm_with_kwargs(self, mock_create, mock_from_env):
        """Test create_llm with full config."""
        config = LLMConfig(
            provider="openai",
            models=["gpt-4"],
            api_key="test",
            timeout=60,
            temperature=0.9,
            max_tokens=2048,
        )
        llm = create_llm(config)
        assert llm is not None
