"""Tests for cost prediction."""

import pytest

from tessera.observability.cost_prediction import CostPredictor


@pytest.mark.unit
class TestCostPredictor:
    """Test cost prediction functionality."""

    def test_predictor_initialization(self):
        """Test predictor initialization."""
        predictor = CostPredictor()

        assert predictor.cost_calc is not None
        assert predictor.metrics_store is not None

    def test_estimate_task_cost_simple(self):
        """Test estimating simple task cost."""
        predictor = CostPredictor()

        estimate = predictor.estimate_task_cost(
            task_description="Create a Python function to add two numbers",
            model="gpt-4",
            provider="openai",
            complexity="simple",
        )

        assert "estimated_prompt_tokens" in estimate
        assert "estimated_completion_tokens" in estimate
        assert "estimated_total_tokens" in estimate
        assert "estimated_cost_usd" in estimate
        assert estimate["confidence"] == "low"

        # Verify tokens estimated
        assert estimate["estimated_prompt_tokens"] > 0
        assert estimate["estimated_completion_tokens"] > 0

    def test_estimate_task_cost_complex(self):
        """Test estimating complex task cost."""
        predictor = CostPredictor()

        simple_est = predictor.estimate_task_cost(
            task_description="Simple task",
            complexity="simple",
        )

        complex_est = predictor.estimate_task_cost(
            task_description="Simple task",
            complexity="complex",
        )

        # Complex should estimate more tokens
        assert complex_est["estimated_total_tokens"] > simple_est["estimated_total_tokens"]
        assert complex_est["estimated_cost_usd"] > simple_est["estimated_cost_usd"]

    def test_estimate_project_cost(self):
        """Test estimating full project cost."""
        predictor = CostPredictor()

        estimate = predictor.estimate_project_cost(
            objective="Build a REST API with authentication",
            num_subtasks=5,
            model="gpt-4",
            provider="openai",
            complexity="medium",
        )

        assert "decomposition_cost" in estimate
        assert "subtasks_cost" in estimate
        assert "total_estimated_cost_usd" in estimate
        assert "total_estimated_tokens" in estimate
        assert estimate["num_subtasks"] == 5

        # Total should be sum of parts
        total = estimate["decomposition_cost"] + estimate["subtasks_cost"]
        assert abs(total - estimate["total_estimated_cost_usd"]) < 0.001

    def test_get_historical_average(self):
        """Test getting historical averages."""
        predictor = CostPredictor()

        averages = predictor.get_historical_average(
            task_type="implementation",
            phase="coding",
            days=30,
        )

        assert "avg_cost_per_task" in averages
        assert "avg_tokens_per_task" in averages
        assert "confidence" in averages

    def test_predict_with_confidence(self):
        """Test prediction with confidence interval."""
        predictor = CostPredictor()

        prediction = predictor.predict_with_confidence(
            task_description="Test task",
            model="gpt-4",
            provider="openai",
        )

        assert "lower_bound_usd" in prediction
        assert "upper_bound_usd" in prediction
        assert "confidence_interval" in prediction

        # Lower bound should be less than upper bound
        assert prediction["lower_bound_usd"] < prediction["upper_bound_usd"]

        # Estimated cost should be within bounds
        cost = prediction["estimated_cost_usd"]
        assert prediction["lower_bound_usd"] <= cost <= prediction["upper_bound_usd"]
