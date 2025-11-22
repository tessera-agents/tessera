"""
Phase execution logic for Tessera workflow.

Manages phase transitions, applies sub-phases to tasks, and tracks progress.
"""

from pathlib import Path
from typing import Any

from tessera.config.schema import WorkflowPhase

from .subphase_handler import SubPhaseHandler


class PhaseExecutor:
    """
    Executes workflow phases with sub-phase application.

    Responsibilities:
    - Determine which phases are required for task complexity
    - Guide supervisor on task creation based on phase context
    - Apply sub-phases to all tasks in current phase
    - Track phase progress and transitions
    """

    def __init__(
        self,
        phases: list[WorkflowPhase],
        complexity: str = "medium",
        project_root: Path = Path(),
    ) -> None:
        """
        Initialize phase executor.

        Args:
            phases: List of workflow phase configurations
            complexity: Task complexity (simple, medium, complex)
            project_root: Project root directory
        """
        self.phases = phases
        self.complexity = complexity
        self.project_root = project_root
        self.subphase_handler = SubPhaseHandler(project_root)

        # Filter phases by complexity
        self.active_phases = self._filter_phases_by_complexity()
        self.current_phase_index = 0

    def _filter_phases_by_complexity(self) -> list[WorkflowPhase]:
        """Filter phases based on task complexity."""
        return [phase for phase in self.phases if self.complexity in phase.required_for_complexity]

    def get_current_phase(self) -> WorkflowPhase | None:
        """Get the current phase."""
        if self.current_phase_index < len(self.active_phases):
            return self.active_phases[self.current_phase_index]
        return None

    def get_phase_by_name(self, name: str) -> WorkflowPhase | None:
        """Get phase by name."""
        for phase in self.active_phases:
            if phase.name == name:
                return phase
        return None

    def advance_to_next_phase(self) -> bool:
        """
        Advance to next phase.

        Returns:
            True if advanced, False if no more phases
        """
        self.current_phase_index += 1
        return self.current_phase_index < len(self.active_phases)

    def get_phase_context(self, phase_name: str | None = None) -> dict[str, Any]:
        """
        Get context for supervisor about current phase.

        Returns task hints and sub-phase requirements for the phase.

        Args:
            phase_name: Optional specific phase name (uses current if None)

        Returns:
            Phase context dict with hints and sub-phases
        """
        phase = self.get_phase_by_name(phase_name) if phase_name else self.get_current_phase()

        if not phase:
            return {}

        return {
            "phase_name": phase.name,
            "description": phase.description,
            "typical_tasks": phase.typical_tasks,
            "suggested_agents": phase.agents,
            "sub_phases": phase.sub_phases,
            "required": phase.required,
        }

    def apply_subphases_to_task(
        self, task_id: str, task_result: Any, phase_name: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Apply all sub-phases for current phase to a completed task.

        Args:
            task_id: Task identifier
            task_result: Task execution result
            phase_name: Optional phase name (uses current if None)

        Returns:
            List of sub-phase execution results
        """
        phase = self.get_phase_by_name(phase_name) if phase_name else self.get_current_phase()

        if not phase or not phase.sub_phases:
            return []

        return self.subphase_handler.execute_all_subphases(
            sub_phases=phase.sub_phases, task_id=task_id, task_result=task_result
        )

    def get_phase_summary(self) -> dict[str, Any]:
        """
        Get summary of all phases and current progress.

        Returns:
            Phase summary dict
        """
        return {
            "total_phases": len(self.active_phases),
            "current_phase_index": self.current_phase_index,
            "current_phase": self.get_current_phase().name if self.get_current_phase() else None,
            "completed_phases": [
                phase.name for phase in self.active_phases[: self.current_phase_index]
            ],
            "remaining_phases": [
                phase.name for phase in self.active_phases[self.current_phase_index + 1 :]
            ],
        }

    def should_create_subtasks(
        self, sub_phase_results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Extract subtasks that need to be created from sub-phase results.

        Args:
            sub_phase_results: Results from apply_subphases_to_task

        Returns:
            List of subtask definitions to create
        """
        subtasks = []

        for result in sub_phase_results:
            if result.get("type") == "subtask" and result.get("created"):
                subtasks.append(result)

        return subtasks

    def execute_phase(self, tasks: list[Any], phase_name: str | None = None) -> dict[str, Any]:
        """
        Execute a complete phase by applying sub-phases to all tasks.

        Args:
            tasks: List of tasks to execute in this phase
            phase_name: Optional phase name (uses current if None)

        Returns:
            Phase execution results
        """
        phase = self.get_phase_by_name(phase_name) if phase_name else self.get_current_phase()

        if not phase:
            return {"status": "no_phase", "results": []}

        results = []
        for task in tasks:
            # Apply sub-phases to this task
            subphase_results = self.apply_subphases_to_task(
                task_id=getattr(task, "task_id", str(id(task))),
                task_result=task,
                phase_name=phase.name,
            )

            results.append(
                {
                    "task": task,
                    "subphase_results": subphase_results,
                    "subtasks_created": self.should_create_subtasks(subphase_results),
                }
            )

        return {
            "phase": phase.name,
            "tasks_processed": len(tasks),
            "results": results,
            "status": "completed",
        }

    def format_subphase_instructions(self, phase_name: str | None = None) -> str:
        """
        Format sub-phase instructions for agent prompt.

        Creates a formatted string describing all sub-phases the agent must follow.

        Args:
            phase_name: Optional phase name (uses current if None)

        Returns:
            Formatted instructions string
        """
        phase = self.get_phase_by_name(phase_name) if phase_name else self.get_current_phase()

        if not phase or not phase.sub_phases:
            return ""

        instructions = [f"\nSUB-PHASE REQUIREMENTS FOR {phase.name.upper()} PHASE:\n"]

        for sp in phase.sub_phases:
            sp_type = sp.get("type")
            sp_name = sp.get("name")
            sp_desc = sp.get("description", "")

            if sp_type == "deliverable":
                outputs = ", ".join(sp.get("outputs", []))
                instructions.append(f"✓ {sp_name}: Must produce {outputs}")
                if sp_desc:
                    instructions.append(f"  ({sp_desc})")

            elif sp_type == "checklist":
                instructions.append(f"✓ {sp_name}: Validate the following:")
                for question in sp.get("questions", []):
                    instructions.append(f"  - {question}")

            elif sp_type == "subtask":
                agent = sp.get("agent", "unknown")
                instructions.append(f"✓ {sp_name}: Will create subtask for {agent}")
                if sp_desc:
                    instructions.append(f"  ({sp_desc})")

        return "\n".join(instructions)
