"""Extended sub-phase handler tests for coverage."""

import pytest
from pathlib import Path
import tempfile

from tessera.workflow.subphase_handler import SubPhaseHandler


@pytest.mark.unit
class TestSubPhaseHandlerExtended:
    """Extended sub-phase handler tests."""

    def test_handle_deliverable_with_glob(self):
        """Test deliverable handling with glob patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create test files
            (project_root / "src").mkdir()
            (project_root / "src" / "main.py").touch()
            (project_root / "src" / "utils.py").touch()

            handler = SubPhaseHandler(project_root)

            sub_phase = {
                "name": "create_source",
                "type": "deliverable",
                "outputs": ["src/*.py"],
            }

            result = handler.handle_deliverable(sub_phase, task_result=None)

            assert result["passed"] is True
            assert len(result["found_files"]) >= 2
            assert "main.py" in str(result["found_files"])

    def test_handle_deliverable_missing_files(self):
        """Test deliverable with missing required files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            handler = SubPhaseHandler(project_root)

            sub_phase = {
                "name": "check_docs",
                "type": "deliverable",
                "outputs": ["README.md", "docs/**/*.md"],
            }

            result = handler.handle_deliverable(sub_phase, task_result=None)

            assert result["passed"] is False
            assert "README.md" in result["missing_files"]
            assert len(result["found_files"]) == 0

    def test_handle_checklist_returns_structure(self):
        """Test checklist handling returns proper structure."""
        handler = SubPhaseHandler()

        sub_phase = {
            "name": "verify_quality",
            "type": "checklist",
            "questions": [
                "Code is formatted?",
                "Tests are passing?",
            ],
        }

        result = handler.handle_checklist(sub_phase, task_result=None)

        assert result["sub_phase"] == "verify_quality"
        assert result["type"] == "checklist"
        assert result["passed"] is True  # Auto-pass in v1.0
        assert len(result["questions"]) == 2
        assert result["answers"] == {}  # Will be populated in future

    def test_handle_subtask_creates_definition(self):
        """Test subtask creation."""
        handler = SubPhaseHandler()

        sub_phase = {
            "name": "security_review",
            "type": "subtask",
            "description": "Perform security audit",
            "agent": "security-expert",
            "depends_on": ["implementation"],
        }

        result = handler.handle_subtask(sub_phase, parent_task_id="task1")

        assert result["sub_phase"] == "security_review"
        assert result["type"] == "subtask"
        assert result["task_id"] == "task1_sub_security_review"
        assert result["description"] == "Perform security audit"
        assert result["agent"] == "security-expert"
        assert result["depends_on"] == ["implementation"]
        assert result["created"] is True

    def test_execute_all_subphases_mixed(self):
        """Test executing multiple sub-phase types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "test.txt").touch()

            handler = SubPhaseHandler(project_root)

            sub_phases = [
                {
                    "name": "check_file",
                    "type": "deliverable",
                    "outputs": ["test.txt"],
                },
                {
                    "name": "verify",
                    "type": "checklist",
                    "questions": ["Quality OK?"],
                },
                {
                    "name": "review",
                    "type": "subtask",
                    "agent": "reviewer",
                },
            ]

            results = handler.execute_all_subphases(
                sub_phases=sub_phases,
                task_id="parent_task",
                task_result=None,
            )

            assert len(results) == 3
            assert results[0]["type"] == "deliverable"
            assert results[0]["passed"] is True
            assert results[1]["type"] == "checklist"
            assert results[2]["type"] == "subtask"
            assert results[2]["created"] is True

    def test_execute_all_subphases_unknown_type(self):
        """Test handling unknown sub-phase type."""
        handler = SubPhaseHandler()

        sub_phases = [
            {
                "name": "unknown_phase",
                "type": "invalid_type",
            },
        ]

        results = handler.execute_all_subphases(
            sub_phases=sub_phases,
            task_id="task1",
            task_result=None,
        )

        assert len(results) == 1
        assert results[0]["passed"] is False
        assert "Unknown sub-phase type" in results[0]["error"]
