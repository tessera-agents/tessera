"""Unit tests for data models."""

from datetime import datetime

import pytest

from tessera.models import (
    AgentConfig,
    AgentResponse,
    Ballot,
    InterviewResult,
    PanelResult,
    QuestionResponse,
    Score,
    ScoreMetrics,
    SubTask,
    Task,
    TaskStatus,
    Vote,
)


@pytest.mark.unit
class TestTaskModels:
    """Test task-related models."""

    def test_subtask_creation(self):
        """Test creating a subtask."""
        subtask = SubTask(
            task_id="test_1",
            description="Test subtask",
            acceptance_criteria=["criterion 1", "criterion 2"],
        )

        assert subtask.task_id == "test_1"
        assert subtask.description == "Test subtask"
        assert subtask.status == TaskStatus.PENDING
        assert len(subtask.acceptance_criteria) == 2
        assert subtask.assigned_to is None

    def test_subtask_with_assignment(self):
        """Test subtask with assignment."""
        subtask = SubTask(
            task_id="test_1",
            description="Test subtask",
            assigned_to="agent_1",
            status=TaskStatus.IN_PROGRESS,
        )

        assert subtask.assigned_to == "agent_1"
        assert subtask.status == TaskStatus.IN_PROGRESS

    def test_task_creation(self):
        """Test creating a task with subtasks."""
        subtasks = [
            SubTask(task_id="sub_1", description="First subtask"),
            SubTask(task_id="sub_2", description="Second subtask"),
        ]

        task = Task(
            task_id="main_task",
            goal="Complete the objective",
            subtasks=subtasks,
        )

        assert task.task_id == "main_task"
        assert task.goal == "Complete the objective"
        assert len(task.subtasks) == 2
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.last_updated, datetime)

    def test_task_status_enum(self):
        """Test task status enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.FAILED.value == "failed"


@pytest.mark.unit
class TestAgentModels:
    """Test agent-related models."""

    def test_agent_response_creation(self):
        """Test creating an agent response."""
        response = AgentResponse(
            agent_name="test_agent",
            task_id="task_1",
            content="This is my response",
        )

        assert response.agent_name == "test_agent"
        assert response.task_id == "task_1"
        assert response.content == "This is my response"
        assert isinstance(response.timestamp, datetime)

    def test_agent_response_with_metadata(self):
        """Test agent response with metadata."""
        response = AgentResponse(
            agent_name="test_agent",
            task_id="task_1",
            content="Response",
            metadata={"key": "value", "score": 95},
        )

        assert response.metadata["key"] == "value"
        assert response.metadata["score"] == 95

    def test_agent_config(self):
        """Test agent configuration."""
        config = AgentConfig(
            name="test_agent",
            role="specialist",
            model="gpt-4",
            temperature=0.5,
            system_prompt="You are a test agent",
        )

        assert config.name == "test_agent"
        assert config.role == "specialist"
        assert config.model == "gpt-4"
        assert config.temperature == 0.5


@pytest.mark.unit
class TestInterviewModels:
    """Test interview-related models."""

    def test_question_response(self):
        """Test question response model."""
        response = QuestionResponse(
            question_id="Q1",
            question_text="What is your approach?",
            answer="My approach involves...",
        )

        assert response.question_id == "Q1"
        assert response.question_text == "What is your approach?"
        assert response.answer == "My approach involves..."
        assert isinstance(response.timestamp, datetime)

    def test_score_metrics_validation(self):
        """Test score metrics validation."""
        metrics = ScoreMetrics(
            accuracy=4.5,
            relevance=5.0,
            completeness=3.0,
            explainability=4.0,
            efficiency=2.5,
            safety=5.0,
        )

        assert metrics.accuracy == 4.5
        assert metrics.safety == 5.0

    def test_score_metrics_bounds(self):
        """Test score metrics are bounded 0-5."""
        with pytest.raises(ValueError):
            ScoreMetrics(
                accuracy=6.0,  # Invalid: > 5
                relevance=3.0,
                completeness=3.0,
                explainability=3.0,
                efficiency=3.0,
                safety=3.0,
            )

        with pytest.raises(ValueError):
            ScoreMetrics(
                accuracy=-1.0,  # Invalid: < 0
                relevance=3.0,
                completeness=3.0,
                explainability=3.0,
                efficiency=3.0,
                safety=3.0,
            )

    def test_score_creation(self):
        """Test creating a score."""
        metrics = ScoreMetrics(
            accuracy=4.0,
            relevance=5.0,
            completeness=3.0,
            explainability=4.0,
            efficiency=3.0,
            safety=5.0,
        )

        score = Score(
            question_id="Q1",
            candidate="test_candidate",
            panelist="interviewer",
            metrics=metrics,
            rationale="Strong technical approach",
            overall_score=82.5,
        )

        assert score.candidate == "test_candidate"
        assert score.overall_score == 82.5
        assert score.rationale == "Strong technical approach"

    def test_interview_result(self):
        """Test interview result model."""
        questions = [
            QuestionResponse(
                question_id="Q1",
                question_text="Question 1",
                answer="Answer 1",
            )
        ]

        result = InterviewResult(
            candidate="test_candidate",
            questions=questions,
            aggregated_score=85.0,
            recommendation="approve - strong candidate",
        )

        assert result.candidate == "test_candidate"
        assert result.aggregated_score == 85.0
        assert len(result.questions) == 1
        assert result.recommendation == "approve - strong candidate"


@pytest.mark.unit
class TestPanelModels:
    """Test panel-related models."""

    def test_vote_enum(self):
        """Test vote enum values."""
        assert Vote.HIRE.value == "hire"
        assert Vote.PASS.value == "pass"

    def test_ballot_creation(self):
        """Test creating a ballot."""
        metrics = ScoreMetrics(
            accuracy=4.0,
            relevance=4.0,
            completeness=4.0,
            explainability=3.0,
            efficiency=3.0,
            safety=4.0,
        )

        ballot = Ballot(
            candidate="candidate_a",
            panelist="technical_panelist",
            vote=Vote.HIRE,
            scores=metrics,
            overall_score=78.0,
            rationale="Good technical skills",
        )

        assert ballot.candidate == "candidate_a"
        assert ballot.vote == Vote.HIRE
        assert ballot.overall_score == 78.0

    def test_panel_result(self):
        """Test panel result model."""
        result = PanelResult(
            session_id="panel_123",
            task_description="Test task",
            candidates=["candidate_a", "candidate_b"],
            panelists=["panelist_1", "panelist_2"],
            decision="candidate_a",
            confidence="high",
        )

        assert result.session_id == "panel_123"
        assert len(result.candidates) == 2
        assert result.decision == "candidate_a"
        assert result.confidence == "high"
        assert result.tie_breaker_used is False

    def test_panel_result_with_tie_breaker(self):
        """Test panel result with tie breaker."""
        result = PanelResult(
            session_id="panel_123",
            task_description="Test task",
            candidates=["candidate_a", "candidate_b"],
            panelists=["panelist_1", "panelist_2"],
            tie_breaker_used=True,
        )

        assert result.tie_breaker_used is True


@pytest.mark.unit
class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_task_to_dict(self):
        """Test task model serialization."""
        task = Task(
            task_id="test_1",
            goal="Test goal",
            subtasks=[SubTask(task_id="sub_1", description="Subtask 1")],
        )

        task_dict = task.model_dump()
        assert task_dict["task_id"] == "test_1"
        assert task_dict["goal"] == "Test goal"
        assert len(task_dict["subtasks"]) == 1

    def test_interview_result_to_dict(self):
        """Test interview result serialization."""
        result = InterviewResult(
            candidate="test_candidate",
            aggregated_score=85.0,
        )

        result_dict = result.model_dump()
        assert result_dict["candidate"] == "test_candidate"
        assert result_dict["aggregated_score"] == 85.0
