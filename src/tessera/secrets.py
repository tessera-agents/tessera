"""
Secure secret management for the autonomy framework.

Supports reading secrets from:
- Environment variables (default)
- 1Password CLI using op:// secret references (recommended)

Example .env configuration:
    # Option 1: Direct environment variables
    GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

    # Option 2: 1Password secret references (recommended)
    OP_GITHUB_ITEM=op://Private/GitHub-Copilot/copilot-token
    OP_OPENAI_ITEM=op://Private/OpenAI-API/credential
    OP_ANTHROPIC_ITEM=op://Private/Anthropic-API/credential
"""

import os
import subprocess

from .logging_config import get_logger

logger = get_logger(__name__)
from typing import Optional
from functools import lru_cache


class SecretManager:
    """Manage secrets from environment variables and 1Password."""

    @staticmethod
    def get_github_token() -> Optional[str]:
        """
        Get GitHub token from:
        1. Environment variable (GITHUB_TOKEN)
        2. 1Password CLI (OP_GITHUB_ITEM must be op:// reference)

        Returns:
            GitHub token or None
        """
        # Try environment variable first
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token

        # Try 1Password CLI with op:// reference
        op_ref = os.getenv("OP_GITHUB_ITEM")
        if op_ref:
            return SecretManager.get_from_1password(op_ref)

        return None

    @staticmethod
    @lru_cache(maxsize=128)
    def get_from_1password(op_reference: str) -> Optional[str]:
        """
        Retrieve a secret from 1Password using op:// secret reference.

        Args:
            op_reference: 1Password secret reference in format:
                         op://vault/item/field
                         Example: op://Private/GitHub-Copilot/copilot-token

        Returns:
            Secret value or None if not found

        Example:
            token = SecretManager.get_from_1password(
                "op://Private/GitHub-Copilot/copilot-token"
            )
        """
        if not op_reference:
            return None

        if not op_reference.startswith("op://"):
            logger.warning(f"1Password reference must start with 'op://': {op_reference}")
            return None

        try:
            # Check if op CLI is available
            result = subprocess.run(
                ["which", "op"],
                capture_output=True,
                text=True,
                timeout=2,
            )

            if result.returncode != 0:
                return None

            # Use op read with secret reference
            result = subprocess.run(
                ["op", "read", "-n", op_reference],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            return result.stdout.strip() if result.stdout else None

        except subprocess.TimeoutExpired:
            logger.warning("1Password CLI timeout")
            return None
        except subprocess.CalledProcessError as e:
            # Item not found or other error
            logger.warning(f"Failed to read from 1Password: {e.stderr if e.stderr else 'unknown error'}")
            return None
        except FileNotFoundError:
            # op command not found
            return None
        except Exception as e:
            logger.warning(f"Error reading from 1Password: {e}")
            return None

    @staticmethod
    def get_openai_api_key() -> Optional[str]:
        """
        Get OpenAI API key from:
        1. Environment variable (OPENAI_API_KEY)
        2. 1Password CLI (OP_OPENAI_ITEM must be op:// reference)

        Returns:
            API key or None
        """
        # Try environment variable first
        key = os.getenv("OPENAI_API_KEY")
        if key:
            return key

        # Try 1Password CLI with op:// reference
        op_ref = os.getenv("OP_OPENAI_ITEM")
        if op_ref:
            return SecretManager.get_from_1password(op_ref)

        return None

    @staticmethod
    def get_anthropic_api_key() -> Optional[str]:
        """
        Get Anthropic API key from:
        1. Environment variable (ANTHROPIC_API_KEY)
        2. 1Password CLI (OP_ANTHROPIC_ITEM must be op:// reference)

        Returns:
            API key or None
        """
        # Try environment variable first
        key = os.getenv("ANTHROPIC_API_KEY")
        if key:
            return key

        # Try 1Password CLI with op:// reference
        op_ref = os.getenv("OP_ANTHROPIC_ITEM")
        if op_ref:
            return SecretManager.get_from_1password(op_ref)

        return None

    @staticmethod
    def check_1password_available() -> bool:
        """
        Check if 1Password CLI is available and authenticated.

        Returns:
            True if 1Password CLI is available and authenticated
        """
        try:
            result = subprocess.run(
                ["op", "account", "list"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def get_all_secrets() -> dict[str, Optional[str]]:
        """
        Get all configured secrets.

        Returns:
            Dictionary of secret names to values
        """
        return {
            "github_token": SecretManager.get_github_token(),
            "openai_api_key": SecretManager.get_openai_api_key(),
            "anthropic_api_key": SecretManager.get_anthropic_api_key(),
        }


# Convenience functions
def get_github_token() -> Optional[str]:
    """Get GitHub token from any configured source."""
    return SecretManager.get_github_token()


def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key from any configured source."""
    return SecretManager.get_openai_api_key()


def get_anthropic_api_key() -> Optional[str]:
    """Get Anthropic API key from any configured source."""
    return SecretManager.get_anthropic_api_key()


def check_secrets_available() -> dict[str, bool]:
    """
    Check which secrets are available.

    Returns:
        Dictionary of secret names to availability status
    """
    secrets = SecretManager.get_all_secrets()
    return {name: value is not None for name, value in secrets.items()}
