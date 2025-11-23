"""
Quality monitoring and iteration control for multi-agent execution.

Monitors code quality, detects loops, and controls iteration based on improvement thresholds.
"""

import hashlib
from pathlib import Path
from typing import Any

from tessera.logging_config import get_logger

logger = get_logger(__name__)


class QualityMonitor:
    """
    Monitors quality metrics and controls iteration.

    Tracks:
    - Test coverage changes
    - Code quality metrics
    - Task output similarity (loop detection)
    - Iteration thresholds
    """

    def __init__(
        self,
        min_coverage_improvement: float = 0.05,
        max_iterations_without_improvement: int = 3,
        similarity_threshold: float = 0.95,
    ) -> None:
        """
        Initialize quality monitor.

        Args:
            min_coverage_improvement: Minimum coverage improvement to continue
            max_iterations_without_improvement: Max iterations without improvement
            similarity_threshold: Threshold for detecting duplicate outputs
        """
        self.min_coverage_improvement = min_coverage_improvement
        self.max_iterations_without_improvement = max_iterations_without_improvement
        self.similarity_threshold = similarity_threshold

        # Tracking
        self.iteration_history: list[dict[str, Any]] = []
        self.output_hashes: dict[str, list[str]] = {}  # task_id -> [hash1, hash2, ...]
        self.coverage_history: list[float] = []

    def record_iteration(
        self,
        iteration: int,
        coverage: float | None = None,
        quality_score: float | None = None,
        tasks_completed: int = 0,
    ) -> None:
        """
        Record metrics for an iteration.

        Args:
            iteration: Iteration number
            coverage: Test coverage percentage
            quality_score: Code quality score
            tasks_completed: Number of tasks completed
        """
        self.iteration_history.append(
            {
                "iteration": iteration,
                "coverage": coverage,
                "quality_score": quality_score,
                "tasks_completed": tasks_completed,
            }
        )

        if coverage is not None:
            self.coverage_history.append(coverage)

    def check_output_similarity(self, task_id: str, output: str) -> float:
        """
        Check if output is similar to previous outputs (loop detection).

        Args:
            task_id: Task identifier
            output: Task output to check

        Returns:
            Similarity score (0.0 = unique, 1.0 = identical)
        """
        # Hash the output
        output_hash = hashlib.sha256(output.encode()).hexdigest()

        # Get previous hashes for this task
        if task_id not in self.output_hashes:
            self.output_hashes[task_id] = []

        previous_hashes = self.output_hashes[task_id]

        # Check if identical to any previous output
        if output_hash in previous_hashes:
            return 1.0  # Identical

        # Store this hash
        self.output_hashes[task_id].append(output_hash)

        # For now, exact match only (can add fuzzy matching later)
        return 0.0

    def detect_loop(self, task_id: str, output: str) -> bool:
        """
        Detect if agent is producing repetitive outputs.

        Args:
            task_id: Task identifier
            output: Task output

        Returns:
            True if loop detected
        """
        similarity = self.check_output_similarity(task_id, output)
        return similarity >= self.similarity_threshold

    def should_continue(self, iteration: int) -> tuple[bool, str]:
        """
        Determine if execution should continue.

        Args:
            iteration: Current iteration number

        Returns:
            Tuple of (should_continue, reason)
        """
        # Check iteration history
        if len(self.iteration_history) < 2:
            return (True, "insufficient_data")

        # Check for improvement in recent iterations
        if len(self.coverage_history) >= self.max_iterations_without_improvement:
            recent_coverage = self.coverage_history[-self.max_iterations_without_improvement :]
            improvements = [recent_coverage[i + 1] - recent_coverage[i] for i in range(len(recent_coverage) - 1)]

            # If no significant improvement
            if all(imp < self.min_coverage_improvement for imp in improvements):
                return (
                    False,
                    f"No coverage improvement in {self.max_iterations_without_improvement} iterations",
                )

        return (True, "quality_improving")

    def get_quality_metrics(self) -> dict[str, Any]:
        """
        Get current quality metrics.

        Returns:
            Dict with quality metrics
        """
        if not self.iteration_history:
            return {"status": "no_data"}

        latest = self.iteration_history[-1]

        return {
            "iterations": len(self.iteration_history),
            "current_coverage": latest.get("coverage"),
            "current_quality_score": latest.get("quality_score"),
            "total_tasks_completed": sum(it.get("tasks_completed", 0) for it in self.iteration_history),
            "coverage_trend": self._calculate_trend(self.coverage_history),
        }

    def _calculate_trend(self, values: list[float]) -> str:
        """
        Calculate trend direction from values.

        Args:
            values: List of numeric values over time

        Returns:
            Trend direction (improving, declining, stable)
        """
        if len(values) < 2:
            return "insufficient_data"

        recent = values[-3:] if len(values) >= 3 else values

        if all(recent[i + 1] > recent[i] for i in range(len(recent) - 1)):
            return "improving"
        if all(recent[i + 1] < recent[i] for i in range(len(recent) - 1)):
            return "declining"

        return "stable"


def check_test_coverage(project_root: Path = Path()) -> float | None:
    """
    Check current test coverage using pytest-cov.

    Args:
        project_root: Project root directory

    Returns:
        Coverage percentage or None if not available
    """
    import os
    import subprocess

    # Prevent runaway if already in pytest (detect pytest env var)
    if os.getenv("PYTEST_CURRENT_TEST"):
        logger.debug("Already in pytest session, skipping coverage check")
        return None

    try:
        result = subprocess.run(
            ["pytest", "--cov=src", "--cov-report=term-missing", "--quiet"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        # Parse coverage from output
        for line in result.stdout.split("\n"):
            if "TOTAL" in line:
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        return float(part.replace("%", ""))

    except Exception as e:
        logger.warning(f"Could not check test coverage: {e}")

    return None
