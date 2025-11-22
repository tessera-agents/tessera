"""
Sub-phase execution handlers.

Handles three types of sub-phases:
1. deliverable - Validates required file outputs
2. checklist - Validates questions are answered
3. subtask - Creates new task assigned to agent
"""

import glob
from pathlib import Path
from typing import Any


class SubPhaseHandler:
    """Handles execution and validation of sub-phases."""

    def __init__(self, project_root: Path = Path()) -> None:
        """
        Initialize sub-phase handler.

        Args:
            project_root: Root directory for deliverable validation
        """
        self.project_root = project_root

    def handle_deliverable(self, sub_phase: dict[str, Any], task_result: Any) -> dict[str, Any]:
        """
        Validate deliverable sub-phase.

        Checks that required files were created.

        Args:
            sub_phase: Deliverable sub-phase config
            task_result: Task execution result

        Returns:
            Validation result with status and missing files
        """
        required_outputs = sub_phase.get("outputs", [])
        missing_files = []
        found_files = []

        for pattern in required_outputs:
            # Expand glob pattern
            matches = list(glob.glob(str(self.project_root / pattern), recursive=True))

            if not matches:
                missing_files.append(pattern)
            else:
                found_files.extend(matches)

        return {
            "sub_phase": sub_phase["name"],
            "type": "deliverable",
            "passed": len(missing_files) == 0,
            "required_outputs": required_outputs,
            "found_files": found_files,
            "missing_files": missing_files,
        }

    def handle_checklist(self, sub_phase: dict[str, Any], task_result: Any) -> dict[str, Any]:
        """
        Execute checklist sub-phase.

        For v0.1, we'll log the questions. In v0.2, agent will answer them.

        Args:
            sub_phase: Checklist sub-phase config
            task_result: Task execution result

        Returns:
            Checklist execution result
        """
        questions = sub_phase.get("questions", [])

        # For v0.1, assume all questions passed
        # v0.2 will actually ask the agent to answer these
        return {
            "sub_phase": sub_phase["name"],
            "type": "checklist",
            "passed": True,  # v0.1: automatic pass, v0.2: actually validate
            "questions": questions,
            "answers": {},  # v0.2: will populate with agent answers
        }

    def handle_subtask(self, sub_phase: dict[str, Any], parent_task_id: str) -> dict[str, Any]:
        """
        Create subtask from sub-phase.

        Args:
            sub_phase: Subtask sub-phase config
            parent_task_id: Parent task ID

        Returns:
            Subtask definition ready for supervisor to assign
        """
        return {
            "sub_phase": sub_phase["name"],
            "type": "subtask",
            "task_id": f"{parent_task_id}_sub_{sub_phase['name']}",
            "description": sub_phase.get("description", f"Subtask: {sub_phase['name']}"),
            "agent": sub_phase.get("agent"),
            "depends_on": sub_phase.get("depends_on", []),
            "created": True,
        }

    def execute_all_subphases(
        self, sub_phases: list[dict[str, Any]], task_id: str, task_result: Any
    ) -> list[dict[str, Any]]:
        """
        Execute all sub-phases for a task.

        Args:
            sub_phases: List of sub-phase configurations
            task_id: Task identifier
            task_result: Task execution result

        Returns:
            List of sub-phase execution results
        """
        results = []

        for sub_phase in sub_phases:
            sp_type = sub_phase.get("type")

            if sp_type == "deliverable":
                result = self.handle_deliverable(sub_phase, task_result)
            elif sp_type == "checklist":
                result = self.handle_checklist(sub_phase, task_result)
            elif sp_type == "subtask":
                result = self.handle_subtask(sub_phase, task_id)
            else:
                # Unknown type
                result = {
                    "sub_phase": sub_phase.get("name", "unknown"),
                    "type": sp_type,
                    "passed": False,
                    "error": f"Unknown sub-phase type: {sp_type}",
                }

            results.append(result)

        return results
