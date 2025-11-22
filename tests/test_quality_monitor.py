"""Tests for quality monitoring."""

from unittest.mock import Mock, patch

import pytest

from tessera.workflow.quality_monitor import QualityMonitor, check_test_coverage


@pytest.mark.unit
class TestQualityMonitor:
    """Test quality monitoring functionality."""

    def test_initialization(self):
        """Test monitor initialization."""
        monitor = QualityMonitor(
            min_coverage_improvement=0.05,
            max_iterations_without_improvement=3,
            similarity_threshold=0.95,
        )

        assert monitor.min_coverage_improvement == 0.05
        assert monitor.max_iterations_without_improvement == 3
        assert monitor.similarity_threshold == 0.95
        assert monitor.iteration_history == []
        assert monitor.output_hashes == {}
        assert monitor.coverage_history == []

    def test_record_iteration(self):
        """Test recording iteration metrics."""
        monitor = QualityMonitor()

        monitor.record_iteration(1, coverage=75.0, quality_score=0.8, tasks_completed=5)

        assert len(monitor.iteration_history) == 1
        assert monitor.iteration_history[0]["iteration"] == 1
        assert monitor.iteration_history[0]["coverage"] == 75.0
        assert monitor.iteration_history[0]["quality_score"] == 0.8
        assert monitor.iteration_history[0]["tasks_completed"] == 5
        assert monitor.coverage_history == [75.0]

    def test_check_output_similarity_new(self):
        """Test similarity check with new output."""
        monitor = QualityMonitor()

        similarity = monitor.check_output_similarity("task1", "output content")

        assert similarity == 0.0  # New output
        assert "task1" in monitor.output_hashes
        assert len(monitor.output_hashes["task1"]) == 1

    def test_check_output_similarity_duplicate(self):
        """Test similarity check with duplicate output."""
        monitor = QualityMonitor()

        # First output
        monitor.check_output_similarity("task1", "same output")

        # Duplicate output
        similarity = monitor.check_output_similarity("task1", "same output")

        assert similarity == 1.0  # Identical
        assert len(monitor.output_hashes["task1"]) == 1  # Same hash stored once initially

    def test_detect_loop_no_loop(self):
        """Test loop detection with unique outputs."""
        monitor = QualityMonitor(similarity_threshold=0.95)

        assert monitor.detect_loop("task1", "output 1") is False
        assert monitor.detect_loop("task1", "output 2") is False

    def test_detect_loop_found(self):
        """Test loop detection with duplicate."""
        monitor = QualityMonitor(similarity_threshold=0.95)

        # First output
        monitor.detect_loop("task1", "same content")

        # Duplicate
        loop_detected = monitor.detect_loop("task1", "same content")

        assert loop_detected is True

    def test_should_continue_insufficient_data(self):
        """Test should_continue with insufficient history."""
        monitor = QualityMonitor()

        should_continue, reason = monitor.should_continue(1)

        assert should_continue is True
        assert reason == "insufficient_data"

    def test_should_continue_with_improvement(self):
        """Test should_continue when quality is improving."""
        monitor = QualityMonitor(
            min_coverage_improvement=0.05, max_iterations_without_improvement=3
        )

        # Record improving coverage
        monitor.record_iteration(1, coverage=70.0)
        monitor.record_iteration(2, coverage=75.0)
        monitor.record_iteration(3, coverage=80.0)

        should_continue, reason = monitor.should_continue(3)

        assert should_continue is True
        assert reason == "quality_improving"

    def test_should_continue_no_improvement(self):
        """Test should_continue when stuck without improvement."""
        monitor = QualityMonitor(
            min_coverage_improvement=0.05, max_iterations_without_improvement=3
        )

        # Record stagnant coverage - all increments below threshold
        monitor.record_iteration(1, coverage=70.0)
        monitor.record_iteration(2, coverage=70.01)  # +0.01 < 0.05
        monitor.record_iteration(3, coverage=70.02)  # +0.01 < 0.05
        monitor.record_iteration(4, coverage=70.03)  # +0.01 < 0.05

        should_continue, reason = monitor.should_continue(4)

        assert should_continue is False
        assert "No coverage improvement" in reason

    def test_get_quality_metrics_no_data(self):
        """Test metrics with no data."""
        monitor = QualityMonitor()

        metrics = monitor.get_quality_metrics()

        assert metrics["status"] == "no_data"

    def test_get_quality_metrics_with_data(self):
        """Test metrics with recorded data."""
        monitor = QualityMonitor()

        monitor.record_iteration(1, coverage=70.0, quality_score=0.7, tasks_completed=3)
        monitor.record_iteration(2, coverage=75.0, quality_score=0.8, tasks_completed=5)

        metrics = monitor.get_quality_metrics()

        assert metrics["iterations"] == 2
        assert metrics["current_coverage"] == 75.0
        assert metrics["current_quality_score"] == 0.8
        assert metrics["total_tasks_completed"] == 8
        assert metrics["coverage_trend"] == "improving"

    def test_calculate_trend_improving(self):
        """Test trend calculation for improving values."""
        monitor = QualityMonitor()

        trend = monitor._calculate_trend([70.0, 75.0, 80.0])

        assert trend == "improving"

    def test_calculate_trend_declining(self):
        """Test trend calculation for declining values."""
        monitor = QualityMonitor()

        trend = monitor._calculate_trend([80.0, 75.0, 70.0])

        assert trend == "declining"

    def test_calculate_trend_stable(self):
        """Test trend calculation for stable values."""
        monitor = QualityMonitor()

        trend = monitor._calculate_trend([75.0, 76.0, 75.0])

        assert trend == "stable"

    def test_calculate_trend_insufficient_data(self):
        """Test trend with insufficient data."""
        monitor = QualityMonitor()

        trend = monitor._calculate_trend([75.0])

        assert trend == "insufficient_data"


@pytest.mark.unit
class TestCoverageCheck:
    """Test coverage checking functionality."""

    @patch("tessera.workflow.quality_monitor.subprocess.run")
    def test_check_test_coverage(self, mock_run):
        """Test coverage check function."""
        # Mock subprocess to avoid spawning pytest
        mock_run.return_value = Mock(
            stdout="TOTAL    100    20    80%\n",
            returncode=0,
        )

        coverage = check_test_coverage()

        # Should parse coverage from output
        assert coverage == 80.0
