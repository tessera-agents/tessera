"""
Tests for sub-phase handler.
"""

import tempfile
from pathlib import Path

import pytest

from tessera.workflow import SubPhaseHandler


@pytest.mark.unit
class TestSubPhaseHandler:
    """Test sub-phase execution handler."""

    def test_handle_deliverable_found(self):
        """Test deliverable validation when files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "output.txt").write_text("test")

            handler = SubPhaseHandler(tmpdir_path)

            sub_phase = {"name": "create_output", "type": "deliverable", "outputs": ["output.txt"]}

            result = handler.handle_deliverable(sub_phase, None)

            assert result["passed"] is True
            assert result["type"] == "deliverable"
            assert len(result["missing_files"]) == 0

    def test_handle_deliverable_missing(self):
        """Test deliverable validation when files missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = SubPhaseHandler(Path(tmpdir))

            sub_phase = {"name": "create_docs", "type": "deliverable", "outputs": ["missing.md"]}

            result = handler.handle_deliverable(sub_phase, None)

            assert result["passed"] is False
            assert "missing.md" in result["missing_files"]

    def test_handle_checklist(self):
        """Test checklist sub-phase execution."""
        handler = SubPhaseHandler()

        sub_phase = {
            "name": "validate",
            "type": "checklist",
            "questions": ["Is it complete?", "Is it tested?"],
        }

        result = handler.handle_checklist(sub_phase, None)

        assert result["type"] == "checklist"
        assert result["passed"] is True  # v0.1 auto-passes
        assert len(result["questions"]) == 2

    def test_handle_subtask(self):
        """Test subtask creation."""
        handler = SubPhaseHandler()

        sub_phase = {
            "name": "code_review",
            "type": "subtask",
            "description": "Review the code",
            "agent": "code-reviewer",
        }

        result = handler.handle_subtask(sub_phase, "parent-task-1")

        assert result["type"] == "subtask"
        assert result["created"] is True
        assert "parent-task-1" in result["task_id"]
        assert result["agent"] == "code-reviewer"

    def test_execute_all_subphases(self):
        """Test executing multiple sub-phases."""
        handler = SubPhaseHandler()

        sub_phases = [
            {"name": "check", "type": "checklist", "questions": ["Q1"]},
            {"name": "review", "type": "subtask", "agent": "reviewer"},
        ]

        results = handler.execute_all_subphases(sub_phases, "task-1", None)

        assert len(results) == 2
        assert results[0]["type"] == "checklist"
        assert results[1]["type"] == "subtask"
