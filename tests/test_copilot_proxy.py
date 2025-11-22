"""Unit tests for Copilot proxy management."""

import subprocess
from unittest.mock import Mock, patch

import pytest
import requests

from tessera.copilot_proxy import (
    CopilotProxyManager,
    get_proxy_manager,
    is_proxy_running,
    start_proxy,
    stop_proxy,
)


@pytest.mark.unit
class TestCopilotProxyManager:
    """Test CopilotProxyManager class."""

    @patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"})
    def test_init_with_env_token(self):
        """Test initialization with token from environment."""
        manager = CopilotProxyManager()
        assert manager.github_token == "test-token"
        assert manager.rate_limit == 30
        assert manager.use_wait is True
        assert manager.port is None  # Uses copilot-api default 4141
        assert manager.verbose is True
        assert manager.process is None
        assert manager._started is False

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        manager = CopilotProxyManager(
            github_token="custom-token",
            rate_limit=60,
            use_wait=False,
            port=4000,
            verbose=False,
        )
        assert manager.github_token == "custom-token"
        assert manager.rate_limit == 60
        assert manager.use_wait is False
        assert manager.port == 4000
        assert manager.verbose is False

    @patch.dict("os.environ", {}, clear=True)
    @patch("tessera.copilot_proxy.CopilotProxyManager._get_github_token")
    def test_get_github_token_from_1password(self, mock_get_token):
        """Test getting GitHub token from 1Password."""
        mock_get_token.return_value = "1password-token"
        manager = CopilotProxyManager()
        assert manager.github_token == "1password-token"

    @patch.dict("os.environ", {}, clear=True)
    @patch("tessera.copilot_proxy.CopilotProxyManager._get_github_token")
    def test_get_github_token_no_token(self, mock_get_token):
        """Test initialization with no token available."""
        mock_get_token.return_value = None
        manager = CopilotProxyManager()
        assert manager.github_token is None

    @patch("subprocess.run")
    def test_is_installed_true(self, mock_run):
        """Test is_installed when copilot-api is available."""
        mock_run.return_value = Mock(returncode=0)
        manager = CopilotProxyManager(github_token="test")

        assert manager.is_installed() is True
        mock_run.assert_called_once_with(
            ["npx", "copilot-api@latest", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )

    @patch("subprocess.run")
    def test_is_installed_false(self, mock_run):
        """Test is_installed when copilot-api is not available."""
        mock_run.return_value = Mock(returncode=1)
        manager = CopilotProxyManager(github_token="test")

        assert manager.is_installed() is False

    @patch("subprocess.run")
    def test_is_installed_timeout(self, mock_run):
        """Test is_installed handles timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)
        manager = CopilotProxyManager(github_token="test")

        assert manager.is_installed() is False

    @patch("subprocess.run")
    def test_is_installed_file_not_found(self, mock_run):
        """Test is_installed handles missing npx."""
        mock_run.side_effect = FileNotFoundError()
        manager = CopilotProxyManager(github_token="test")

        assert manager.is_installed() is False

    @patch("subprocess.run")
    def test_install_success(self, mock_run):
        """Test successful installation."""
        mock_run.return_value = Mock(returncode=0)
        manager = CopilotProxyManager(github_token="test")

        assert manager.install() is True
        mock_run.assert_called_once_with(
            ["npm", "install", "-g", "copilot-api@latest"],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )

    @patch("subprocess.run")
    def test_install_failure(self, mock_run):
        """Test failed installation."""
        mock_run.return_value = Mock(returncode=1)
        manager = CopilotProxyManager(github_token="test")

        assert manager.install() is False

    @patch("subprocess.run")
    def test_install_timeout(self, mock_run):
        """Test installation timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 120)
        manager = CopilotProxyManager(github_token="test")

        assert manager.install() is False

    def test_start_already_started(self):
        """Test starting when already started."""
        manager = CopilotProxyManager(github_token="test")
        manager._started = True

        assert manager.start() is True

    @patch.dict("os.environ", {}, clear=True)
    @patch("tessera.copilot_proxy.CopilotProxyManager._get_github_token")
    def test_start_no_token(self, mock_get_token):
        """Test starting without GitHub token raises error."""
        # Ensure get_github_token returns None
        mock_get_token.return_value = None

        manager = CopilotProxyManager(github_token=None)

        with pytest.raises(ValueError, match="GitHub Copilot token required"):
            manager.start()

    def test_start_invalid_token_format_ghp(self):
        """Test starting with GitHub PAT (ghp_) token raises error."""
        manager = CopilotProxyManager(github_token="ghp_FAKE_GITHUB_PAT_FOR_TESTING")

        with pytest.raises(ValueError, match="Invalid GitHub Copilot token format"):
            manager.start()

    def test_start_invalid_token_format_gho(self):
        """Test starting with GitHub OAuth token (gho_) raises error."""
        manager = CopilotProxyManager(github_token="gho_someOAuthTokenHere")

        with pytest.raises(ValueError, match="Invalid GitHub Copilot token format"):
            manager.start()

    def test_start_invalid_token_format_generic(self):
        """Test starting with generic invalid token raises error."""
        manager = CopilotProxyManager(github_token="invalid-token-123")

        with pytest.raises(ValueError, match="Invalid GitHub Copilot token format"):
            manager.start()

    def test_start_token_error_message_content_ghp(self):
        """Test that error message for ghp_ token mentions PAT."""
        manager = CopilotProxyManager(github_token="ghp_somePatToken")

        with pytest.raises(ValueError) as exc_info:
            manager.start()

        error_msg = str(exc_info.value)
        assert "ghp_***" in error_msg
        assert "ghu_***" in error_msg
        assert "GitHub PAT" in error_msg or "ghp_*" in error_msg
        assert "npx copilot-api@latest auth" in error_msg

    @patch.dict("os.environ", {}, clear=True)
    @patch("tessera.copilot_proxy.CopilotProxyManager._get_github_token")
    def test_start_token_error_message_content_no_token(self, mock_get_token):
        """Test that error message for missing token has helpful instructions."""
        mock_get_token.return_value = None
        manager = CopilotProxyManager(github_token=None)

        with pytest.raises(ValueError) as exc_info:
            manager.start()

        error_msg = str(exc_info.value)
        assert "npx copilot-api@latest auth" in error_msg
        assert "ghu_" in error_msg
        assert "ghp_*" in error_msg or "NOT supported" in error_msg

    @patch("subprocess.Popen")
    @patch.dict("os.environ", {}, clear=False)
    def test_start_valid_ghu_token(self, mock_popen):
        """Test starting with valid ghu_ token proceeds."""
        mock_process = Mock()
        mock_popen.return_value = mock_process

        manager = CopilotProxyManager(github_token="ghu_FAKE_TEST_TOKEN_NOT_REAL")
        result = manager.start(wait_for_ready=False)

        assert result is True
        assert manager._started is True
        mock_popen.assert_called_once()

    def test_stop_no_process(self):
        """Test stopping when no process is running."""
        manager = CopilotProxyManager(github_token="test")
        manager.stop()  # Should not raise

    @patch("subprocess.run")
    def test_install_file_not_found(self, mock_run):
        """Test installation when npm is not found."""
        mock_run.side_effect = FileNotFoundError()
        manager = CopilotProxyManager(github_token="test")

        assert manager.install() is False

    @patch("subprocess.Popen")
    @patch.dict("os.environ", {}, clear=False)
    def test_start_success_no_wait(self, mock_popen):
        """Test starting proxy without waiting for ready."""
        mock_process = Mock()
        mock_popen.return_value = mock_process

        manager = CopilotProxyManager(github_token="ghu_FAKE_TEST_ONLY")
        result = manager.start(wait_for_ready=False)

        assert result is True
        assert manager._started is True
        assert manager.process == mock_process
        mock_popen.assert_called_once()

    @patch("subprocess.Popen")
    @patch("tessera.copilot_proxy.CopilotProxyManager.wait_for_ready")
    @patch.dict("os.environ", {}, clear=False)
    def test_start_success_with_wait(self, mock_wait, mock_popen):
        """Test starting proxy with wait for ready."""
        mock_process = Mock()
        mock_popen.return_value = mock_process
        mock_wait.return_value = True

        manager = CopilotProxyManager(github_token="ghu_FAKE_TEST_ONLY")
        result = manager.start(wait_for_ready=True)

        assert result is True
        mock_wait.assert_called_once()

    @patch("subprocess.Popen")
    @patch("tessera.copilot_proxy.CopilotProxyManager.wait_for_ready")
    @patch.dict("os.environ", {}, clear=False)
    def test_start_wait_fails(self, mock_wait, mock_popen):
        """Test starting proxy when wait for ready fails."""
        mock_process = Mock()
        mock_popen.return_value = mock_process
        mock_wait.return_value = False

        manager = CopilotProxyManager(github_token="ghu_FAKE_TEST_ONLY")
        result = manager.start(wait_for_ready=True)

        assert result is False
        mock_wait.assert_called_once()

    @patch("subprocess.Popen")
    @patch.dict("os.environ", {}, clear=False)
    def test_start_popen_file_not_found(self, mock_popen):
        """Test starting when npx is not found."""
        mock_popen.side_effect = FileNotFoundError()

        manager = CopilotProxyManager(github_token="ghu_FAKE_TEST_ONLY")
        result = manager.start(wait_for_ready=False)

        assert result is False

    @patch("subprocess.Popen")
    @patch.dict("os.environ", {}, clear=False)
    def test_start_popen_generic_exception(self, mock_popen):
        """Test starting with generic exception."""
        mock_popen.side_effect = Exception("Something went wrong")

        manager = CopilotProxyManager(github_token="ghu_FAKE_TEST_ONLY")
        result = manager.start(wait_for_ready=False)

        assert result is False

    @patch("requests.get")
    @patch("time.time")
    @patch("time.sleep")
    @patch("subprocess.Popen")
    @patch.dict("os.environ", {}, clear=False)
    def test_wait_for_ready_success(self, mock_popen, mock_sleep, mock_time, mock_get):
        """Test wait_for_ready when server becomes ready."""
        mock_process = Mock()
        mock_popen.return_value = mock_process
        mock_time.side_effect = [0, 1]  # First call, second call

        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        manager = CopilotProxyManager(github_token="test-token", port=3000)
        manager.process = mock_process

        result = manager.wait_for_ready(timeout=30.0)

        assert result is True
        mock_get.assert_called()

    @patch("requests.get")
    @patch("time.time")
    @patch("time.sleep")
    @patch("subprocess.Popen")
    @patch.dict("os.environ", {}, clear=False)
    def test_wait_for_ready_timeout(self, mock_popen, mock_sleep, mock_time, mock_get):
        """Test wait_for_ready when timeout occurs."""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process still running
        mock_popen.return_value = mock_process
        # Simulate timeout by making time always exceed timeout
        mock_time.side_effect = [0, 40]  # Start, then timeout

        mock_get.side_effect = requests.exceptions.RequestException()

        manager = CopilotProxyManager(github_token="test-token", port=3000)
        manager.process = mock_process

        result = manager.wait_for_ready(timeout=30.0)

        assert result is False

    @patch("requests.get")
    @patch("time.time")
    @patch("time.sleep")
    @patch("subprocess.Popen")
    @patch.dict("os.environ", {}, clear=False)
    def test_wait_for_ready_process_died(self, mock_popen, mock_sleep, mock_time, mock_get):
        """Test wait_for_ready when process dies."""
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process exited with code 1
        mock_process.returncode = 1
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = "Error message"
        mock_popen.return_value = mock_process
        mock_time.side_effect = [0, 1]

        mock_get.side_effect = requests.exceptions.RequestException()

        manager = CopilotProxyManager(github_token="test-token", port=3000)
        manager.process = mock_process

        result = manager.wait_for_ready(timeout=30.0)

        assert result is False

    def test_stop_graceful(self):
        """Test graceful stop."""
        manager = CopilotProxyManager(github_token="test-token")
        mock_process = Mock()
        mock_process.wait = Mock()  # Successful graceful shutdown
        manager.process = mock_process
        manager._started = True

        manager.stop()

        assert manager.process is None
        assert manager._started is False
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()

    def test_stop_force_kill(self):
        """Test force kill when graceful shutdown times out."""
        manager = CopilotProxyManager(github_token="test-token")
        mock_process = Mock()
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired("cmd", 5),  # First wait times out
            None,  # Second wait after kill succeeds
        ]
        manager.process = mock_process
        manager._started = True

        manager.stop()

        assert manager.process is None
        assert manager._started is False
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    def test_stop_exception_handling(self):
        """Test stop handles exceptions gracefully."""
        manager = CopilotProxyManager(github_token="test-token")
        mock_process = Mock()
        mock_process.terminate.side_effect = Exception("Something went wrong")
        manager.process = mock_process
        manager._started = True

        # Should not raise
        manager.stop()

        assert manager.process is None
        assert manager._started is False

    def test_is_running_false_not_started(self):
        """Test is_running when not started."""
        manager = CopilotProxyManager(github_token="test-token")
        assert manager.is_running() is False

    def test_is_running_false_process_died(self):
        """Test is_running when process died."""
        manager = CopilotProxyManager(github_token="test-token")
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process exited
        manager.process = mock_process
        manager._started = True

        result = manager.is_running()

        assert result is False
        assert manager._started is False

    @patch("requests.get")
    def test_is_running_true(self, mock_get):
        """Test is_running when server is responsive."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        manager = CopilotProxyManager(github_token="test-token", port=3000)
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process still running
        manager.process = mock_process
        manager._started = True

        result = manager.is_running()

        assert result is True
        mock_get.assert_called_once_with("http://localhost:3000/health", timeout=2.0)

    @patch("requests.get")
    def test_is_running_request_fails(self, mock_get):
        """Test is_running when health check request fails."""
        mock_get.side_effect = requests.exceptions.RequestException()

        manager = CopilotProxyManager(github_token="test-token", port=3000)
        mock_process = Mock()
        mock_process.poll.return_value = None
        manager.process = mock_process
        manager._started = True

        result = manager.is_running()

        assert result is False

    def test_get_base_url(self):
        """Test get_base_url returns correct URL."""
        # Test with custom port
        manager = CopilotProxyManager(github_token="test-token", port=4000)
        assert manager.get_base_url() == "http://localhost:4000/v1"

        # Test with default port
        manager_default = CopilotProxyManager(github_token="test-token")
        assert manager_default.get_base_url() == "http://localhost:4141/v1"

    @patch("tessera.copilot_proxy.CopilotProxyManager.start")
    @patch("tessera.copilot_proxy.CopilotProxyManager.stop")
    def test_context_manager(self, mock_stop, mock_start):
        """Test context manager protocol."""
        manager = CopilotProxyManager(github_token="test-token")

        with manager as m:
            assert m == manager
            mock_start.assert_called_once()

        mock_stop.assert_called_once()


@pytest.mark.unit
class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch("tessera.copilot_proxy.get_proxy_manager")
    def test_start_proxy(self, mock_get_manager):
        """Test start_proxy convenience function."""
        mock_manager = Mock()
        mock_manager.start.return_value = True
        mock_get_manager.return_value = mock_manager

        result = start_proxy(github_token="ghu_testToken123", rate_limit=60, use_wait=False)

        assert result is True
        mock_get_manager.assert_called_once_with(
            github_token="ghu_testToken123", rate_limit=60, use_wait=False
        )
        mock_manager.start.assert_called_once_with(wait_for_ready=True)

    @patch("tessera.copilot_proxy._proxy_instance", None)
    def test_stop_proxy_no_instance(self):
        """Test stop_proxy when no instance exists."""
        # Should not raise
        stop_proxy()

    @patch("tessera.copilot_proxy._proxy_instance")
    def test_stop_proxy_with_instance(self, mock_instance):
        """Test stop_proxy with existing instance."""
        mock_instance.stop = Mock()

        stop_proxy()

        mock_instance.stop.assert_called_once()

    @patch("tessera.copilot_proxy._proxy_instance", None)
    def test_is_proxy_running_no_instance(self):
        """Test is_proxy_running when no instance exists."""
        assert is_proxy_running() is False

    @patch("tessera.copilot_proxy._proxy_instance")
    def test_is_proxy_running_with_instance(self, mock_instance):
        """Test is_proxy_running with existing instance."""
        mock_instance.is_running.return_value = True

        result = is_proxy_running()

        assert result is True
        mock_instance.is_running.assert_called_once()

    @patch("tessera.copilot_proxy.CopilotProxyManager")
    @patch("tessera.copilot_proxy._proxy_instance", None)
    def test_get_proxy_manager_creates_instance(self, mock_manager_class):
        """Test get_proxy_manager creates new instance."""
        mock_instance = Mock()
        mock_manager_class.return_value = mock_instance

        result = get_proxy_manager(github_token="ghu_testToken123", rate_limit=45)

        assert result == mock_instance
        mock_manager_class.assert_called_once_with(
            github_token="ghu_testToken123", rate_limit=45, use_wait=True, port=None, verbose=True
        )

    def test_get_proxy_manager_returns_existing(self):
        """Test get_proxy_manager returns existing instance."""
        # First create an instance
        with patch("tessera.copilot_proxy._proxy_instance", None):
            with patch("tessera.copilot_proxy.CopilotProxyManager") as mock_class:
                mock_instance = Mock()
                mock_class.return_value = mock_instance

                first_result = get_proxy_manager()

                # Call again - should return same instance without creating new
                second_result = get_proxy_manager()

                assert first_result == second_result
                # Should only create instance once
                assert mock_class.call_count == 1
