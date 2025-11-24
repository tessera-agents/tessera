"""
Sub-phase model definitions for workflow phases.

Sub-phases are standard operating procedures applied to all tasks within a phase.
"""

from typing import Literal

from pydantic import BaseModel, Field


class SubPhaseDeliverable(BaseModel):
    """
    Deliverable sub-phase - requires specific file outputs.

    Example:
        All architecture tasks must produce diagrams and ADRs.
    """

    name: str
    type: Literal["deliverable"] = "deliverable"
    description: str = ""
    required: bool = True
    outputs: list[str] = Field(default_factory=list)  # Glob patterns: "*.svg", "docs/adr/*.md"


class SubPhaseChecklist(BaseModel):
    """
    Checklist sub-phase - validation questions to answer.

    Example:
        All architecture tasks must validate: "Is this scalable?", "Is this secure?"
    """

    name: str
    type: Literal["checklist"] = "checklist"
    description: str = ""
    required: bool = True
    questions: list[str] = Field(default_factory=list)


class SubPhaseSubtask(BaseModel):
    """
    Subtask sub-phase - creates new task assigned to agent.

    Example:
        All architecture tasks require peer review (creates subtask for senior-architect).
    """

    name: str
    type: Literal["subtask"] = "subtask"
    description: str = ""
    required: bool = True
    agent: str  # Which agent handles this subtask
    depends_on: list[str] = Field(default_factory=list)  # Other sub-phase names


# Union type for all sub-phases
SubPhase = SubPhaseDeliverable | SubPhaseChecklist | SubPhaseSubtask
