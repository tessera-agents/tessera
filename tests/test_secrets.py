"""Unit tests for secret management."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from tessera.secrets import (
    SecretManager,
    check_secrets_available,
    get_anthropic_api_key,
    get_github_token,
    get_openai_api_key,
)


@pytest.mark.unit
class TestSecretManager:
    """Test SecretManager class."""

    @patch.dict("os.environ", {"GITHUB_TOKEN": "env-token"})
    def test_get_github_token_from_env(self):
        """Test getting GitHub token from environment."""
        token = SecretManager.get_github_token()
        assert token == "env-token"

    @patch.dict("os.environ", {"OP_GITHUB_ITEM": "op://Private/test/token"}, clear=True)
    @patch("tessera.secrets.SecretManager.get_from_1password")
    def test_get_github_token_from_1password(self, mock_1pass):
        """Test getting GitHub token from 1Password."""
        mock_1pass.return_value = "1pass-token"

        token = SecretManager.get_github_token()

        assert token == "1pass-token"
        mock_1pass.assert_called_once_with("op://Private/test/token")

    @patch.dict("os.environ", {"OP_GITHUB_ITEM": "op://Work/CustomItem/secret"}, clear=True)
    @patch("tessera.secrets.SecretManager.get_from_1password")
    def test_get_github_token_custom_item(self, mock_1pass):
        """Test getting GitHub token with custom op:// reference."""
        mock_1pass.return_value = "custom-token"

        SecretManager.get_github_token()

        mock_1pass.assert_called_once_with("op://Work/CustomItem/secret")

    @patch.dict("os.environ", {}, clear=True)
    def test_get_github_token_no_config(self):
        """Test getting GitHub token with no configuration."""
        token = SecretManager.get_github_token()

        assert token is None

    @patch.dict("os.environ", {}, clear=True)
    @patch("tessera.secrets.SecretManager.get_from_1password")
    def test_get_github_token_not_found(self, mock_1pass):
        """Test getting GitHub token when not available."""
        mock_1pass.return_value = None

        token = SecretManager.get_github_token()

        assert token is None

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env-key"})
    def test_get_openai_api_key_from_env(self):
        """Test getting OpenAI API key from environment."""
        key = SecretManager.get_openai_api_key()
        assert key == "sk-env-key"

    @patch.dict("os.environ", {"OP_OPENAI_ITEM": "op://Private/OpenAI/credential"}, clear=True)
    @patch("tessera.secrets.SecretManager.get_from_1password")
    def test_get_openai_api_key_from_1password(self, mock_1pass):
        """Test getting OpenAI API key from 1Password."""
        mock_1pass.return_value = "sk-1pass-key"

        key = SecretManager.get_openai_api_key()

        assert key == "sk-1pass-key"
        mock_1pass.assert_called_once_with("op://Private/OpenAI/credential")

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-env-key"})
    def test_get_anthropic_api_key_from_env(self):
        """Test getting Anthropic API key from environment."""
        key = SecretManager.get_anthropic_api_key()
        assert key == "sk-ant-env-key"

    @patch.dict("os.environ", {"OP_ANTHROPIC_ITEM": "op://Private/Anthropic/credential"}, clear=True)
    @patch("tessera.secrets.SecretManager.get_from_1password")
    def test_get_anthropic_api_key_from_1password(self, mock_1pass):
        """Test getting Anthropic API key from 1Password."""
        mock_1pass.return_value = "sk-ant-1pass-key"

        key = SecretManager.get_anthropic_api_key()

        assert key == "sk-ant-1pass-key"
        mock_1pass.assert_called_once_with("op://Private/Anthropic/credential")

    @patch("subprocess.run")
    def test_get_from_1password_op_not_installed(self, mock_run):
        """Test get_from_1password when op CLI not installed."""
        mock_run.return_value = Mock(returncode=1)

        result = SecretManager.get_from_1password("op://Test/Item/password")

        assert result is None

    @patch("subprocess.run")
    def test_get_from_1password_with_op_reference(self, mock_run):
        """Test get_from_1password with op:// reference."""
        # Clear cache to ensure fresh test
        SecretManager.get_from_1password.cache_clear()

        # First call: check if op is available
        # Second call: get item
        mock_run.side_effect = [
            Mock(returncode=0),  # which op
            Mock(returncode=0, stdout="secret-value\n"),
        ]

        result = SecretManager.get_from_1password("op://Private/TestItem/password")

        assert result == "secret-value"
        assert mock_run.call_count == 2
        # Check second call args
        call_args = mock_run.call_args_list[1][0][0]
        assert call_args == ["op", "read", "-n", "op://Private/TestItem/password"]

    @patch("subprocess.run")
    def test_get_from_1password_with_different_vault(self, mock_run):
        """Test get_from_1password with different vault in op:// reference."""
        SecretManager.get_from_1password.cache_clear()

        mock_run.side_effect = [
            Mock(returncode=0),  # which op
            Mock(returncode=0, stdout="secret-value\n"),
        ]

        result = SecretManager.get_from_1password("op://Work/item-id/password")

        assert result == "secret-value"
        call_args = mock_run.call_args_list[1][0][0]
        assert call_args == ["op", "read", "-n", "op://Work/item-id/password"]

    @patch("subprocess.run")
    def test_get_from_1password_invalid_reference(self, mock_run):
        """Test get_from_1password with invalid reference (not op://)."""
        SecretManager.get_from_1password.cache_clear()

        result = SecretManager.get_from_1password("not-an-op-reference")

        assert result is None
        # Should not call op command
        assert mock_run.call_count == 0

    @patch("subprocess.run")
    def test_get_from_1password_timeout(self, mock_run):
        """Test get_from_1password timeout."""
        SecretManager.get_from_1password.cache_clear()

        mock_run.side_effect = [
            Mock(returncode=0),  # which op
            subprocess.TimeoutExpired("cmd", 10),
        ]

        result = SecretManager.get_from_1password("op://Private/test/password")

        assert result is None

    @patch("subprocess.run")
    def test_get_from_1password_item_not_found(self, mock_run):
        """Test get_from_1password when item not found."""
        SecretManager.get_from_1password.cache_clear()

        mock_run.side_effect = [
            Mock(returncode=0),  # which op
            subprocess.CalledProcessError(1, "cmd", stderr="item not found"),
        ]

        result = SecretManager.get_from_1password("op://Private/test/password")

        assert result is None

    @patch("subprocess.run")
    def test_get_from_1password_op_command_not_found(self, mock_run):
        """Test get_from_1password when op command not found."""
        SecretManager.get_from_1password.cache_clear()

        mock_run.side_effect = FileNotFoundError()

        result = SecretManager.get_from_1password("op://Private/test/password")

        assert result is None

    @patch("subprocess.run")
    def test_get_from_1password_generic_error(self, mock_run):
        """Test get_from_1password with generic error."""
        SecretManager.get_from_1password.cache_clear()

        mock_run.side_effect = [
            Mock(returncode=0),  # which op
            RuntimeError("Unknown error"),
        ]

        result = SecretManager.get_from_1password("op://Private/test/password")

        assert result is None

    @patch("subprocess.run")
    def test_get_from_1password_empty_output(self, mock_run):
        """Test get_from_1password with empty output."""
        SecretManager.get_from_1password.cache_clear()

        mock_run.side_effect = [
            Mock(returncode=0),  # which op
            Mock(returncode=0, stdout=""),
        ]

        result = SecretManager.get_from_1password("op://Private/test/password")

        assert result is None

    @patch("subprocess.run")
    def test_check_1password_available_true(self, mock_run):
        """Test check_1password_available when available."""
        mock_run.return_value = Mock(returncode=0)

        result = SecretManager.check_1password_available()

        assert result is True
        mock_run.assert_called_once_with(
            ["op", "account", "list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )

    @patch("subprocess.run")
    def test_check_1password_available_false(self, mock_run):
        """Test check_1password_available when not available."""
        mock_run.return_value = Mock(returncode=1)

        result = SecretManager.check_1password_available()

        assert result is False

    @patch("subprocess.run")
    def test_check_1password_available_exception(self, mock_run):
        """Test check_1password_available with exception."""
        mock_run.side_effect = OSError("Error")

        result = SecretManager.check_1password_available()

        assert result is False

    @patch("tessera.secrets.SecretManager.get_github_token")
    @patch("tessera.secrets.SecretManager.get_openai_api_key")
    @patch("tessera.secrets.SecretManager.get_anthropic_api_key")
    def test_get_all_secrets(self, mock_anthropic, mock_openai, mock_github):
        """Test get_all_secrets."""
        mock_github.return_value = "gh-token"
        mock_openai.return_value = "openai-key"
        mock_anthropic.return_value = "anthropic-key"

        secrets = SecretManager.get_all_secrets()

        assert secrets == {
            "github_token": "gh-token",
            "openai_api_key": "openai-key",
            "anthropic_api_key": "anthropic-key",
        }


@pytest.mark.unit
class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    @patch("tessera.secrets.SecretManager.get_github_token")
    def test_get_github_token(self, mock_method):
        """Test get_github_token convenience function."""
        mock_method.return_value = "token"

        result = get_github_token()

        assert result == "token"
        mock_method.assert_called_once()

    @patch("tessera.secrets.SecretManager.get_openai_api_key")
    def test_get_openai_api_key(self, mock_method):
        """Test get_openai_api_key convenience function."""
        mock_method.return_value = "key"

        result = get_openai_api_key()

        assert result == "key"
        mock_method.assert_called_once()

    @patch("tessera.secrets.SecretManager.get_anthropic_api_key")
    def test_get_anthropic_api_key(self, mock_method):
        """Test get_anthropic_api_key convenience function."""
        mock_method.return_value = "key"

        result = get_anthropic_api_key()

        assert result == "key"
        mock_method.assert_called_once()

    @patch("tessera.secrets.SecretManager.get_all_secrets")
    def test_check_secrets_available(self, mock_get_all):
        """Test check_secrets_available function."""
        mock_get_all.return_value = {
            "github_token": "token",
            "openai_api_key": None,
            "anthropic_api_key": "key",
        }

        result = check_secrets_available()

        assert result == {
            "github_token": True,
            "openai_api_key": False,
            "anthropic_api_key": True,
        }
