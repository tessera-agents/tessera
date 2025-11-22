"""
Tests for phase executor.
"""

import pytest
from unittest.mock import Mock

from tessera.config.schema import WorkflowPhase
from tessera.workflow import PhaseExecutor


@pytest.mark.unit
class TestPhaseExecutor:
    """Test phase executor functionality."""

    def test_filter_phases_by_complexity(self):
        """Test phases are filtered by complexity."""
        phases = [
            WorkflowPhase(name="simple-phase", required_for_complexity=["simple"]),
            WorkflowPhase(name="complex-phase", required_for_complexity=["complex"]),
            WorkflowPhase(
                name="all-phase", required_for_complexity=["simple", "medium", "complex"]
            ),
        ]

        executor = PhaseExecutor(phases, complexity="simple")

        # Should include simple-phase and all-phase, not complex-phase
        active_names = [p.name for p in executor.active_phases]
        assert "simple-phase" in active_names
        assert "all-phase" in active_names
        assert "complex-phase" not in active_names

    def test_get_current_phase(self):
        """Test getting current phase."""
        phases = [
            WorkflowPhase(name="phase1"),
            WorkflowPhase(name="phase2"),
        ]

        executor = PhaseExecutor(phases)

        current = executor.get_current_phase()
        assert current.name == "phase1"

    def test_advance_to_next_phase(self):
        """Test advancing through phases."""
        phases = [
            WorkflowPhase(name="phase1"),
            WorkflowPhase(name="phase2"),
        ]

        executor = PhaseExecutor(phases)

        # Start at phase1
        assert executor.get_current_phase().name == "phase1"

        # Advance
        has_next = executor.advance_to_next_phase()
        assert has_next is True
        assert executor.get_current_phase().name == "phase2"

        # No more phases
        has_next = executor.advance_to_next_phase()
        assert has_next is False

    def test_get_phase_context(self):
        """Test getting phase context for supervisor."""
        phases = [
            WorkflowPhase(
                name="implementation",
                description="Code implementation",
                typical_tasks=["Write code", "Add tests"],
                agents=["python-expert"],
                sub_phases=[{"name": "write_tests", "type": "deliverable"}],
            ),
        ]

        executor = PhaseExecutor(phases)
        context = executor.get_phase_context()

        assert context["phase_name"] == "implementation"
        assert context["description"] == "Code implementation"
        assert "Write code" in context["typical_tasks"]
        assert "python-expert" in context["suggested_agents"]
        assert len(context["sub_phases"]) == 1

    def test_get_phase_summary(self):
        """Test phase summary generation."""
        phases = [
            WorkflowPhase(name="phase1"),
            WorkflowPhase(name="phase2"),
            WorkflowPhase(name="phase3"),
        ]

        executor = PhaseExecutor(phases)
        executor.advance_to_next_phase()  # Move to phase2

        summary = executor.get_phase_summary()

        assert summary["total_phases"] == 3
        assert summary["current_phase_index"] == 1
        assert summary["current_phase"] == "phase2"
        assert "phase1" in summary["completed_phases"]
        assert "phase3" in summary["remaining_phases"]

    def test_execute_phase(self):
        """Test executing a complete phase."""
        phases = [
            WorkflowPhase(
                name="implementation",
                sub_phases=[
                    {
                        "name": "write_code",
                        "type": "deliverable",
                        "outputs": ["src/**/*.py"],
                    },
                    {
                        "name": "verify_quality",
                        "type": "checklist",
                        "questions": ["Code follows style guide?", "Tests added?"],
                    },
                ],
            ),
        ]

        executor = PhaseExecutor(phases)

        # Create mock tasks
        task1 = Mock(task_id="t1")
        task2 = Mock(task_id="t2")

        result = executor.execute_phase([task1, task2])

        assert result["phase"] == "implementation"
        assert result["tasks_processed"] == 2
        assert len(result["results"]) == 2
        assert result["status"] == "completed"

    def test_execute_phase_no_phase(self):
        """Test execute_phase when no current phase."""
        executor = PhaseExecutor([])

        result = executor.execute_phase([Mock()])

        assert result["status"] == "no_phase"
        assert result["results"] == []
