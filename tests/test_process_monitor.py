"""Tests for process monitoring functionality."""

from unittest.mock import MagicMock, Mock, patch

import psutil
import pytest

from tessera.workflow.process_monitor import ProcessMonitor, get_process_monitor


@pytest.fixture(autouse=True)
def _mock_atexit() -> None:
    """Mock atexit to prevent cleanup on test teardown."""
    with patch("tessera.workflow.process_monitor.atexit.register"):
        yield


class TestProcessMonitor:
    """Test process monitor."""

    def test_initialization(self) -> None:
        """Test monitor initialization."""
        monitor = ProcessMonitor()

        assert monitor.tracked_processes == {}
        assert monitor.parent_pid is not None
        assert isinstance(monitor.parent_pid, int)

    def test_register_process_with_psutil(self) -> None:
        """Test registering a psutil process."""
        monitor = ProcessMonitor()

        mock_process = MagicMock(spec=psutil.Process)
        mock_process.pid = 12345

        monitor.register_process(
            mock_process,
            name="test_process",
            task_id="task1",
            agent_name="agent1",
        )

        assert 12345 in monitor.tracked_processes
        assert monitor.tracked_processes[12345]["name"] == "test_process"
        assert monitor.tracked_processes[12345]["task_id"] == "task1"
        assert monitor.tracked_processes[12345]["agent_name"] == "agent1"

    def test_register_process_with_popen(self) -> None:
        """Test registering a subprocess.Popen process."""
        monitor = ProcessMonitor()

        mock_process = MagicMock()
        mock_process.pid = 54321

        monitor.register_process(mock_process, name="popen_process")

        assert 54321 in monitor.tracked_processes
        assert monitor.tracked_processes[54321]["name"] == "popen_process"

    def test_register_process_without_pid(self) -> None:
        """Test registering a process without pid attribute."""
        monitor = ProcessMonitor()

        mock_process = MagicMock(spec=[])  # No pid attribute

        monitor.register_process(mock_process, name="no_pid")

        # Should not be registered
        assert len(monitor.tracked_processes) == 0

    def test_unregister_process(self) -> None:
        """Test unregistering a process."""
        monitor = ProcessMonitor()

        mock_process = MagicMock()
        mock_process.pid = 12345

        monitor.register_process(mock_process, name="test")
        assert 12345 in monitor.tracked_processes

        monitor.unregister_process(12345)
        assert 12345 not in monitor.tracked_processes

    def test_unregister_nonexistent_process(self) -> None:
        """Test unregistering non-existent process."""
        monitor = ProcessMonitor()

        # Should not raise
        monitor.unregister_process(99999)

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_check_for_runaways_normal_process(self, mock_process_class: Mock) -> None:
        """Test checking for runaways with normal processes."""
        monitor = ProcessMonitor()

        # Register a process
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        monitor.register_process(mock_proc, name="normal", task_id="task1")

        # Mock psutil.Process
        mock_ps_proc = MagicMock()
        mock_ps_proc.is_running.return_value = True
        mock_ps_proc.cpu_percent.return_value = 50.0  # Normal CPU
        mock_ps_proc.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
        mock_process_class.return_value = mock_ps_proc

        runaways = monitor.check_for_runaways()

        assert runaways == []

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_check_for_runaways_high_cpu(self, mock_process_class: Mock) -> None:
        """Test checking for runaways with high CPU usage."""
        monitor = ProcessMonitor()

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        monitor.register_process(mock_proc, name="cpu_hog", task_id="task1")

        # Mock psutil.Process with high CPU
        mock_ps_proc = MagicMock()
        mock_ps_proc.is_running.return_value = True
        mock_ps_proc.cpu_percent.return_value = 95.0  # High CPU
        mock_ps_proc.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_process_class.return_value = mock_ps_proc

        runaways = monitor.check_for_runaways()

        assert len(runaways) == 1
        assert runaways[0]["pid"] == 12345
        assert runaways[0]["name"] == "cpu_hog"
        assert runaways[0]["cpu_percent"] == 95.0

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_check_for_runaways_high_memory(self, mock_process_class: Mock) -> None:
        """Test checking for runaways with high memory usage."""
        monitor = ProcessMonitor()

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        monitor.register_process(mock_proc, name="mem_hog")

        # Mock psutil.Process with high memory
        mock_ps_proc = MagicMock()
        mock_ps_proc.is_running.return_value = True
        mock_ps_proc.cpu_percent.return_value = 50.0
        mock_ps_proc.memory_info.return_value.rss = 2000 * 1024 * 1024  # 2GB
        mock_process_class.return_value = mock_ps_proc

        runaways = monitor.check_for_runaways()

        assert len(runaways) == 1
        assert runaways[0]["memory_mb"] > 1024

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_check_for_runaways_terminated_process(self, mock_process_class: Mock) -> None:
        """Test checking for runaways with terminated process."""
        monitor = ProcessMonitor()

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        monitor.register_process(mock_proc, name="terminated")

        # Mock psutil.Process as not running
        mock_ps_proc = MagicMock()
        mock_ps_proc.is_running.return_value = False
        mock_process_class.return_value = mock_ps_proc

        runaways = monitor.check_for_runaways()

        assert runaways == []
        # Process should be unregistered
        assert 12345 not in monitor.tracked_processes

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_check_for_runaways_no_such_process(self, mock_process_class: Mock) -> None:
        """Test checking for runaways when process doesn't exist."""
        monitor = ProcessMonitor()

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        monitor.register_process(mock_proc, name="gone")

        # Mock psutil.Process raising NoSuchProcess
        mock_process_class.side_effect = psutil.NoSuchProcess(12345)

        runaways = monitor.check_for_runaways()

        assert runaways == []
        # Process should be unregistered
        assert 12345 not in monitor.tracked_processes

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_check_for_runaways_access_denied(self, mock_process_class: Mock) -> None:
        """Test checking for runaways with access denied."""
        monitor = ProcessMonitor()

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        monitor.register_process(mock_proc, name="denied")

        # Mock psutil.Process raising AccessDenied
        mock_process_class.side_effect = psutil.AccessDenied(12345)

        runaways = monitor.check_for_runaways()

        assert runaways == []
        # Process should be unregistered
        assert 12345 not in monitor.tracked_processes

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_get_process_count(self, mock_process_class: Mock) -> None:
        """Test getting process count."""
        monitor = ProcessMonitor()

        # Register some processes
        for i in range(3):
            mock_proc = MagicMock()
            mock_proc.pid = 12345 + i
            monitor.register_process(mock_proc, name=f"proc{i}")

        # Mock all processes as running
        mock_ps_proc = MagicMock()
        mock_ps_proc.is_running.return_value = True
        mock_process_class.return_value = mock_ps_proc

        count = monitor.get_process_count()

        assert count == 3

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_get_process_count_cleans_terminated(self, mock_process_class: Mock) -> None:
        """Test that get_process_count cleans up terminated processes."""
        monitor = ProcessMonitor()

        # Register processes
        for i in range(3):
            mock_proc = MagicMock()
            mock_proc.pid = 12345 + i
            monitor.register_process(mock_proc, name=f"proc{i}")

        # Mock one process as terminated
        def mock_process_factory(pid: int) -> MagicMock:
            mock_ps_proc = MagicMock()
            if pid == 12346:  # Middle process is terminated
                mock_ps_proc.is_running.return_value = False
            else:
                mock_ps_proc.is_running.return_value = True
            return mock_ps_proc

        mock_process_class.side_effect = mock_process_factory

        count = monitor.get_process_count()

        assert count == 2
        assert 12346 not in monitor.tracked_processes

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_kill_process_graceful(self, mock_process_class: Mock) -> None:
        """Test gracefully killing a process."""
        monitor = ProcessMonitor()

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        monitor.register_process(mock_proc, name="to_kill")

        # Mock psutil.Process
        mock_ps_proc = MagicMock()
        mock_process_class.return_value = mock_ps_proc

        result = monitor.kill_process(12345, force=False)

        assert result is True
        mock_ps_proc.terminate.assert_called_once()
        mock_ps_proc.kill.assert_not_called()
        mock_ps_proc.wait.assert_called_once_with(timeout=5)
        assert 12345 not in monitor.tracked_processes

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_kill_process_force(self, mock_process_class: Mock) -> None:
        """Test force killing a process."""
        monitor = ProcessMonitor()

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        monitor.register_process(mock_proc, name="to_kill")

        # Mock psutil.Process
        mock_ps_proc = MagicMock()
        mock_process_class.return_value = mock_ps_proc

        result = monitor.kill_process(12345, force=True)

        assert result is True
        mock_ps_proc.kill.assert_called_once()
        mock_ps_proc.terminate.assert_not_called()

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_kill_process_no_such_process(self, mock_process_class: Mock) -> None:
        """Test killing non-existent process."""
        monitor = ProcessMonitor()

        mock_process_class.side_effect = psutil.NoSuchProcess(12345)

        result = monitor.kill_process(12345)

        assert result is False

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_kill_process_access_denied(self, mock_process_class: Mock) -> None:
        """Test killing process with access denied."""
        monitor = ProcessMonitor()

        mock_process_class.side_effect = psutil.AccessDenied(12345)

        result = monitor.kill_process(12345)

        assert result is False

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_kill_process_timeout(self, mock_process_class: Mock) -> None:
        """Test killing process that times out."""
        monitor = ProcessMonitor()

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        monitor.register_process(mock_proc, name="to_kill")

        # Mock psutil.Process timing out
        mock_ps_proc = MagicMock()
        mock_ps_proc.wait.side_effect = psutil.TimeoutExpired(5)
        mock_process_class.return_value = mock_ps_proc

        result = monitor.kill_process(12345)

        assert result is False

    def test_cleanup_all_empty(self) -> None:
        """Test cleanup with no tracked processes."""
        monitor = ProcessMonitor()

        # Should not raise
        monitor.cleanup_all()

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_cleanup_all(self, mock_process_class: Mock) -> None:
        """Test cleaning up all processes."""
        monitor = ProcessMonitor()

        # Register processes
        for i in range(3):
            mock_proc = MagicMock()
            mock_proc.pid = 12345 + i
            monitor.register_process(mock_proc, name=f"proc{i}")

        # Mock psutil.Process
        mock_ps_proc = MagicMock()
        mock_process_class.return_value = mock_ps_proc

        monitor.cleanup_all()

        # All processes should be terminated
        assert mock_ps_proc.terminate.call_count == 3

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_cleanup_all_with_errors(self, mock_process_class: Mock) -> None:
        """Test cleanup handling errors gracefully."""
        monitor = ProcessMonitor()

        # Register processes
        for i in range(3):
            mock_proc = MagicMock()
            mock_proc.pid = 12345 + i
            monitor.register_process(mock_proc, name=f"proc{i}")

        # Mock psutil.Process raising errors
        def mock_process_factory(pid: int) -> MagicMock:
            mock_ps_proc = MagicMock()
            if pid == 12346:  # Middle process raises error
                mock_ps_proc.terminate.side_effect = OSError("Error")
            return mock_ps_proc

        mock_process_class.side_effect = mock_process_factory

        # Should not raise
        monitor.cleanup_all()

    @patch("tessera.workflow.process_monitor.psutil.Process")
    def test_get_status_summary(self, mock_process_class: Mock) -> None:
        """Test getting status summary."""
        monitor = ProcessMonitor()

        # Register processes
        mock_proc1 = MagicMock()
        mock_proc1.pid = 12345
        monitor.register_process(mock_proc1, name="proc1", task_id="task1", agent_name="agent1")

        mock_proc2 = MagicMock()
        mock_proc2.pid = 12346
        monitor.register_process(mock_proc2, name="proc2")

        # Mock psutil.Process
        mock_ps_proc = MagicMock()
        mock_ps_proc.is_running.return_value = True
        mock_ps_proc.cpu_percent.return_value = 50.0
        mock_ps_proc.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_process_class.return_value = mock_ps_proc

        summary = monitor.get_status_summary()

        assert summary["total_tracked"] == 2
        assert len(summary["processes"]) == 2
        assert summary["processes"][0]["pid"] == 12345
        assert summary["processes"][0]["name"] == "proc1"
        assert summary["processes"][0]["task_id"] == "task1"
        assert summary["processes"][0]["agent_name"] == "agent1"


class TestGlobalMonitor:
    """Test global process monitor singleton."""

    def test_get_process_monitor_singleton(self) -> None:
        """Test that get_process_monitor returns singleton."""
        monitor1 = get_process_monitor()
        monitor2 = get_process_monitor()

        assert monitor1 is monitor2

    def test_get_process_monitor_creates_instance(self) -> None:
        """Test that get_process_monitor creates instance."""
        # Clear global
        import tessera.workflow.process_monitor

        tessera.workflow.process_monitor._process_monitor = None

        monitor = get_process_monitor()

        assert isinstance(monitor, ProcessMonitor)
