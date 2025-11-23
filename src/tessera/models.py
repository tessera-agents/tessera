"""
Data models for the autonomy framework.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class SubTask(BaseModel):
    """A subtask within a larger task."""

    task_id: str
    description: str
    assigned_to: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    acceptance_criteria: list[str] = Field(default_factory=list)
    due_by: datetime | None = None
    dependencies: list[str] = Field(default_factory=list)
    result: str | None = None


class Task(BaseModel):
    """A task to be executed by agents."""

    task_id: str
    goal: str
    subtasks: list[SubTask] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Response from an agent."""

    agent_name: str
    task_id: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuestionResponse(BaseModel):
    """Response to an interview question."""

    question_id: str
    question_text: str
    answer: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ScoreMetrics(BaseModel):
    """Scoring metrics for evaluation."""

    accuracy: float = Field(ge=0, le=5, description="Accuracy score (0-5)")
    relevance: float = Field(ge=0, le=5, description="Relevance score (0-5)")
    completeness: float = Field(ge=0, le=5, description="Completeness score (0-5)")
    explainability: float = Field(ge=0, le=5, description="Explainability score (0-5)")
    efficiency: float = Field(ge=0, le=5, description="Efficiency score (0-5)")
    safety: float = Field(ge=0, le=5, description="Safety score (0-5)")


class Score(BaseModel):
    """A score from a panelist or interviewer."""

    question_id: str
    candidate: str
    panelist: str
    metrics: ScoreMetrics
    rationale: str
    overall_score: float = Field(ge=0, le=100, description="Weighted overall score (0-100)")


class InterviewResult(BaseModel):
    """Result of an interview process."""

    candidate: str
    questions: list[QuestionResponse] = Field(default_factory=list)
    scores: list[Score] = Field(default_factory=list)
    aggregated_score: float = 0.0
    ranking: int | None = None
    recommendation: str | None = None
    weaknesses: list[str] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)
    transcript: dict[str, Any] = Field(default_factory=dict)


class Vote(str, Enum):
    """Vote options for panel decisions."""

    HIRE = "hire"
    PASS = "pass"


class Ballot(BaseModel):
    """A panelist's ballot."""

    candidate: str
    panelist: str
    vote: Vote
    scores: ScoreMetrics
    overall_score: float = Field(ge=0, le=100)
    rationale: str


class PanelResult(BaseModel):
    """Result of a panel interview."""

    session_id: str
    task_description: str
    candidates: list[str]
    panelists: list[str]
    ballots: list[Ballot] = Field(default_factory=list)
    final_ranking: list[tuple[str, float]] = Field(default_factory=list)
    decision: str | None = None
    confidence: str = "medium"  # low, medium, high
    tie_breaker_used: bool = False
    transcript: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class AgentConfig(BaseModel):
    """Configuration for an agent."""

    name: str
    role: str
    model: str = "gpt-4-turbo-preview"
    temperature: float = 0.7
    max_tokens: int | None = None
    system_prompt: str
    metadata: dict[str, Any] = Field(default_factory=dict)
