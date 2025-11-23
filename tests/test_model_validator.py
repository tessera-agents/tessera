"""Unit tests for model validator."""

from unittest.mock import Mock, patch

import pytest
import requests

from tessera.config import LLMConfig
from tessera.model_validator import (
    ModelValidator,
    list_available_models,
    validate_config_models,
)


@pytest.mark.unit
class TestModelValidatorFetchModels:
    """Test ModelValidator.fetch_available_models()."""

    @patch("requests.get")
    def test_fetch_available_models_success(self, mock_get):
        """Test successfully fetching models."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-4", "object": "model"},
                {"id": "gpt-3.5-turbo", "object": "model"},
                {"id": "o1-preview", "object": "model"},
            ]
        }
        mock_get.return_value = mock_response

        result = ModelValidator.fetch_available_models("http://localhost:3000/v1", "test-key")

        assert result == ["gpt-4", "gpt-3.5-turbo", "o1-preview"]
        mock_get.assert_called_once_with(
            "http://localhost:3000/v1/models",
            headers={"Authorization": "Bearer test-key", "Content-Type": "application/json"},
            timeout=10.0,
        )

    @patch("requests.get")
    def test_fetch_available_models_url_normalization(self, mock_get):
        """Test that base_url gets /v1 appended if missing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
        mock_get.return_value = mock_response

        ModelValidator.fetch_available_models(
            "http://localhost:3000",  # No /v1
            "test-key",
        )

        # Should append /v1
        mock_get.assert_called_once()
        assert mock_get.call_args[0][0] == "http://localhost:3000/v1/models"

    @patch("requests.get")
    def test_fetch_available_models_url_with_trailing_slash(self, mock_get):
        """Test URL normalization with trailing slash."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
        mock_get.return_value = mock_response

        ModelValidator.fetch_available_models(
            "http://localhost:3000/",  # Trailing slash
            "test-key",
        )

        # Should strip and append /v1
        assert mock_get.call_args[0][0] == "http://localhost:3000/v1/models"

    @patch("requests.get")
    def test_fetch_available_models_non_200_status(self, mock_get):
        """Test handling non-200 status code."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_get.return_value = mock_response

        result = ModelValidator.fetch_available_models("http://localhost:3000/v1", "test-key")

        assert result is None

    @patch("requests.get")
    def test_fetch_available_models_unexpected_format(self, mock_get):
        """Test handling unexpected response format (no 'data' key)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": ["gpt-4"]}  # Wrong format
        mock_get.return_value = mock_response

        result = ModelValidator.fetch_available_models("http://localhost:3000/v1", "test-key")

        assert result is None

    @patch("requests.get")
    def test_fetch_available_models_timeout(self, mock_get):
        """Test handling timeout error."""
        mock_get.side_effect = requests.exceptions.Timeout()

        result = ModelValidator.fetch_available_models("http://localhost:3000/v1", "test-key")

        assert result is None

    @patch("requests.get")
    def test_fetch_available_models_connection_error(self, mock_get):
        """Test handling connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError()

        result = ModelValidator.fetch_available_models("http://localhost:3000/v1", "test-key")

        assert result is None

    @patch("requests.get")
    def test_fetch_available_models_generic_exception(self, mock_get):
        """Test handling generic exception."""
        mock_get.side_effect = Exception("Something went wrong")

        result = ModelValidator.fetch_available_models("http://localhost:3000/v1", "test-key")

        assert result is None

    @patch("requests.get")
    def test_fetch_available_models_custom_timeout(self, mock_get):
        """Test using custom timeout value."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
        mock_get.return_value = mock_response

        ModelValidator.fetch_available_models("http://localhost:3000/v1", "test-key", timeout=30.0)

        assert mock_get.call_args[1]["timeout"] == 30.0


@pytest.mark.unit
class TestModelValidatorValidateModels:
    """Test ModelValidator.validate_models()."""

    def test_validate_models_no_base_url_skips_validation(self):
        """Test that validation is skipped when no base_url is configured."""
        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=["gpt-4"],
            base_url=None,  # No proxy
        )

        result = ModelValidator.validate_models(config)

        assert result is True

    @patch("tessera.model_validator.ModelValidator.fetch_available_models")
    def test_validate_models_no_models_strict_mode_exits(self, mock_fetch):
        """Test that strict mode exits when no models configured."""
        mock_fetch.return_value = ["gpt-4", "gpt-3.5-turbo"]

        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=[],  # No models
            base_url="http://localhost:3000/v1",
        )

        with pytest.raises(SystemExit) as exc_info:
            ModelValidator.validate_models(config, strict=True)

        assert exc_info.value.code == 1
        mock_fetch.assert_called_once()

    @patch("tessera.model_validator.ModelValidator.fetch_available_models")
    def test_validate_models_no_models_non_strict(self, mock_fetch):
        """Test that non-strict mode returns False when no models configured."""
        mock_fetch.return_value = ["gpt-4", "gpt-3.5-turbo"]

        config = LLMConfig(provider="openai", api_key="test-key", models=[], base_url="http://localhost:3000/v1")

        result = ModelValidator.validate_models(config, strict=False)

        assert result is False

    @patch("tessera.model_validator.ModelValidator.fetch_available_models")
    def test_validate_models_fetch_fails_strict_mode_exits(self, mock_fetch):
        """Test that strict mode exits when fetch fails."""
        mock_fetch.return_value = None  # Fetch failed

        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=["gpt-4"],
            base_url="http://localhost:3000/v1",
        )

        with pytest.raises(SystemExit) as exc_info:
            ModelValidator.validate_models(config, strict=True)

        assert exc_info.value.code == 1

    @patch("tessera.model_validator.ModelValidator.fetch_available_models")
    def test_validate_models_fetch_fails_non_strict(self, mock_fetch):
        """Test that non-strict mode returns False when fetch fails."""
        mock_fetch.return_value = None

        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=["gpt-4"],
            base_url="http://localhost:3000/v1",
        )

        result = ModelValidator.validate_models(config, strict=False)

        assert result is False

    @patch("tessera.model_validator.ModelValidator.fetch_available_models")
    def test_validate_models_all_valid(self, mock_fetch):
        """Test successful validation when all models are valid."""
        mock_fetch.return_value = ["gpt-4", "gpt-3.5-turbo", "o1-preview"]

        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=["gpt-4", "gpt-3.5-turbo"],
            base_url="http://localhost:3000/v1",
        )

        result = ModelValidator.validate_models(config, strict=True)

        assert result is True

    @patch("tessera.model_validator.ModelValidator.fetch_available_models")
    def test_validate_models_some_invalid_strict_exits(self, mock_fetch):
        """Test that strict mode exits when some models are invalid."""
        mock_fetch.return_value = ["gpt-4", "gpt-3.5-turbo"]

        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=["gpt-4", "invalid-model"],
            base_url="http://localhost:3000/v1",
        )

        with pytest.raises(SystemExit) as exc_info:
            ModelValidator.validate_models(config, strict=True)

        assert exc_info.value.code == 1

    @patch("tessera.model_validator.ModelValidator.fetch_available_models")
    def test_validate_models_some_invalid_non_strict(self, mock_fetch):
        """Test that non-strict mode returns False when some models invalid."""
        mock_fetch.return_value = ["gpt-4", "gpt-3.5-turbo"]

        config = LLMConfig(
            provider="openai",
            api_key="test-key",
            models=["gpt-4", "invalid-model"],
            base_url="http://localhost:3000/v1",
        )

        result = ModelValidator.validate_models(config, strict=False)

        assert result is False


@pytest.mark.unit
class TestModelValidatorDisplayModels:
    """Test ModelValidator.display_available_models()."""

    @patch("tessera.model_validator.ModelValidator.fetch_available_models")
    def test_display_available_models_success(self, mock_fetch):
        """Test displaying available models successfully."""
        mock_fetch.return_value = ["gpt-4", "gpt-3.5-turbo", "o1-preview"]

        # Should not raise
        ModelValidator.display_available_models("http://localhost:3000/v1", "test-key")

        mock_fetch.assert_called_once_with("http://localhost:3000/v1", "test-key")

    @patch("tessera.model_validator.ModelValidator.fetch_available_models")
    def test_display_available_models_more_than_three(self, mock_fetch):
        """Test displaying more than 3 models shows count."""
        mock_fetch.return_value = ["gpt-4", "gpt-3.5-turbo", "o1-preview", "gpt-4-32k", "claude-3"]

        # Should not raise
        ModelValidator.display_available_models("http://localhost:3000/v1", "test-key")

        mock_fetch.assert_called_once()

    @patch("tessera.model_validator.ModelValidator.fetch_available_models")
    def test_display_available_models_fetch_fails(self, mock_fetch):
        """Test displaying when fetch fails."""
        mock_fetch.return_value = None

        # Should not raise, just print error
        ModelValidator.display_available_models("http://localhost:3000/v1", "test-key")

        mock_fetch.assert_called_once()


@pytest.mark.unit
class TestConvenienceFunctions:
    """Test convenience wrapper functions."""

    @patch("tessera.model_validator.ModelValidator.validate_models")
    def test_validate_config_models(self, mock_validate):
        """Test validate_config_models convenience function."""
        mock_validate.return_value = True

        config = LLMConfig(provider="openai", api_key="test-key", models=["gpt-4"])

        result = validate_config_models(config, strict=False)

        assert result is True
        mock_validate.assert_called_once_with(config, strict=False)

    @patch("tessera.model_validator.ModelValidator.display_available_models")
    def test_list_available_models(self, mock_display):
        """Test list_available_models convenience function."""
        list_available_models(base_url="http://custom:3000/v1", api_key="custom-key")

        mock_display.assert_called_once_with("http://custom:3000/v1", "custom-key")

    @patch("tessera.model_validator.ModelValidator.display_available_models")
    def test_list_available_models_defaults(self, mock_display):
        """Test list_available_models with default arguments."""
        list_available_models()

        mock_display.assert_called_once_with("http://localhost:3000/v1", "dummy")
