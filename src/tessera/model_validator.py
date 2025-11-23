"""
Model validation utilities for verifying available models from LLM providers.
"""

import sys

import requests

from .config import LLMConfig


class ModelValidator:
    """Validate configured models against provider's available models."""

    @staticmethod
    def fetch_available_models(base_url: str, api_key: str, timeout: float = 10.0) -> list[str] | None:
        """
        Fetch available models from the /v1/models endpoint.

        Args:
            base_url: Base URL for the API (e.g., "http://localhost:3000/v1")
            api_key: API key for authentication
            timeout: Request timeout in seconds

        Returns:
            List of available model IDs, or None if request fails
        """
        try:
            # Ensure base_url ends with /v1
            if not base_url.endswith("/v1"):
                base_url = base_url.rstrip("/") + "/v1"

            models_url = f"{base_url}/models"

            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            response = requests.get(models_url, headers=headers, timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                # OpenAI-compatible response format
                if "data" in data:
                    return [model["id"] for model in data["data"]]
                return None
            return None

        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.ConnectionError:
            return None
        except Exception:
            return None

    @staticmethod
    def validate_models(config: LLMConfig, strict: bool = True) -> bool:
        """
        Validate that configured models are available.

        Args:
            config: LLM configuration to validate
            strict: If True, exit on validation failure. If False, just warn.

        Returns:
            True if validation passed, False otherwise
        """
        # Only validate if using a proxy (base_url is set)
        if not config.base_url:
            return True

        # If no models configured, this is an error
        if not config.models:
            # Fetch and display available models
            available = ModelValidator.fetch_available_models(config.base_url, config.api_key)
            if available:
                for _i, model in enumerate(available, 1):
                    pass

            if strict:
                sys.exit(1)
            return False

        # Fetch available models
        available_models = ModelValidator.fetch_available_models(config.base_url, config.api_key)

        if available_models is None:
            if strict:
                sys.exit(1)
            return False

        # Check each configured model

        invalid_models = []
        valid_models = []

        for model in config.models:
            if model in available_models:
                valid_models.append(model)
            else:
                invalid_models.append(model)

        if invalid_models:
            for _i, model in enumerate(available_models, 1):
                pass

            if strict:
                sys.exit(1)
            return False

        return True

    @staticmethod
    def display_available_models(base_url: str, api_key: str) -> None:
        """
        Display all available models from the provider.

        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
        """

        models = ModelValidator.fetch_available_models(base_url, api_key)

        if models:
            for _i, _model in enumerate(models, 1):
                pass
            if len(models) > 3:
                pass
        else:
            pass


def validate_config_models(config: LLMConfig, strict: bool = True) -> bool:
    """
    Convenience function to validate models in an LLMConfig.

    Args:
        config: Configuration to validate
        strict: If True, exit on failure. If False, just warn.

    Returns:
        True if validation passed
    """
    return ModelValidator.validate_models(config, strict=strict)


def list_available_models(base_url: str = "http://localhost:3000/v1", api_key: str = "dummy") -> None:
    """
    Convenience function to list available models.

    Args:
        base_url: Base URL for the API
        api_key: API key for authentication
    """
    ModelValidator.display_available_models(base_url, api_key)
