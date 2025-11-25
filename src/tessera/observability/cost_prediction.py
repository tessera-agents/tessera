"""
Cost prediction for task execution.

Estimates costs before execution based on historical data and task complexity.
"""

from typing import Any

from ..logging_config import get_logger
from .cost import CostCalculator
from .metrics import MetricsStore

logger = get_logger(__name__)


class CostPredictor:
    """
    Predicts execution costs before running tasks.

    Uses historical data and task analysis for estimation.
    """

    def __init__(
        self,
        cost_calc: CostCalculator | None = None,
        metrics_store: MetricsStore | None = None,
    ) -> None:
        """
        Initialize cost predictor.

        Args:
            cost_calc: Cost calculator instance
            metrics_store: Metrics store for historical data
        """
        self.cost_calc = cost_calc or CostCalculator()
        self.metrics_store = metrics_store or MetricsStore()

    def estimate_task_cost(
        self,
        task_description: str,
        model: str = "gpt-4",
        provider: str = "openai",
        complexity: str = "medium",
    ) -> dict[str, Any]:
        """
        Estimate cost for a single task.

        Args:
            task_description: Task description
            model: LLM model to use
            provider: LLM provider
            complexity: Task complexity (simple, medium, complex)

        Returns:
            Cost estimate with breakdown
        """
        # Estimate tokens based on description length and complexity
        description_tokens = len(task_description.split()) * 2  # Rough estimate

        # Complexity multipliers
        complexity_factors = {
            "simple": 1.5,
            "medium": 3.0,
            "complex": 6.0,
        }

        factor = complexity_factors.get(complexity, 3.0)

        # Estimate prompt and completion tokens
        estimated_prompt_tokens = int(description_tokens * factor)
        estimated_completion_tokens = int(estimated_prompt_tokens * 0.6)  # Typical ratio

        # Calculate cost
        estimated_cost = self.cost_calc.calculate(
            prompt_tokens=estimated_prompt_tokens,
            completion_tokens=estimated_completion_tokens,
            model=model,
            provider=provider,
        )

        return {
            "estimated_prompt_tokens": estimated_prompt_tokens,
            "estimated_completion_tokens": estimated_completion_tokens,
            "estimated_total_tokens": estimated_prompt_tokens + estimated_completion_tokens,
            "estimated_cost_usd": estimated_cost,
            "confidence": "low",  # Rough estimate
        }

    def estimate_project_cost(
        self,
        objective: str,
        num_subtasks: int = 5,
        model: str = "gpt-4",
        provider: str = "openai",
        complexity: str = "medium",
    ) -> dict[str, Any]:
        """
        Estimate total cost for a project.

        Args:
            objective: Project objective
            num_subtasks: Estimated number of subtasks
            model: LLM model
            provider: LLM provider
            complexity: Overall complexity

        Returns:
            Project cost estimate
        """
        # Estimate supervisor decomposition cost
        decomposition_est = self.estimate_task_cost(
            task_description=objective,
            model=model,
            provider=provider,
            complexity=complexity,
        )

        # Estimate subtask execution costs
        # Assume average subtask is half the complexity of main task
        avg_subtask_length = len(objective) // (num_subtasks + 1)
        avg_subtask_desc = " ".join(objective.split()[:avg_subtask_length])

        subtask_complexity = {
            "simple": "simple",
            "medium": "simple",
            "complex": "medium",
        }.get(complexity, "simple")

        subtask_est = self.estimate_task_cost(
            task_description=avg_subtask_desc,
            model=model,
            provider=provider,
            complexity=subtask_complexity,
        )

        total_subtask_cost = subtask_est["estimated_cost_usd"] * num_subtasks

        total_estimated_cost = decomposition_est["estimated_cost_usd"] + total_subtask_cost
        total_estimated_tokens = (
            decomposition_est["estimated_total_tokens"] + subtask_est["estimated_total_tokens"] * num_subtasks
        )

        return {
            "decomposition_cost": decomposition_est["estimated_cost_usd"],
            "subtasks_cost": total_subtask_cost,
            "total_estimated_cost_usd": total_estimated_cost,
            "total_estimated_tokens": total_estimated_tokens,
            "num_subtasks": num_subtasks,
            "model": model,
            "provider": provider,
            "confidence": "low",
        }

    def get_historical_average(
        self,
        task_type: str | None = None,
        phase: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Get historical average costs.

        Args:
            task_type: Optional task type filter
            phase: Optional phase filter
            days: Number of days to analyze

        Returns:
            Historical cost averages
        """
        # This would query metrics_store for actual historical data
        # For now, return placeholder

        return {
            "avg_cost_per_task": 0.05,
            "avg_tokens_per_task": 2000,
            "sample_size": 0,
            "confidence": "none",
        }

    def predict_with_confidence(
        self,
        task_description: str,
        model: str = "gpt-4",
        provider: str = "openai",
    ) -> dict[str, Any]:
        """
        Predict cost with confidence interval.

        Args:
            task_description: Task description
            model: LLM model
            provider: LLM provider

        Returns:
            Prediction with confidence bounds
        """
        base_estimate = self.estimate_task_cost(task_description, model, provider)

        # Add confidence interval (±30% for rough estimates)
        cost = base_estimate["estimated_cost_usd"]
        lower_bound = cost * 0.7
        upper_bound = cost * 1.3

        return {
            **base_estimate,
            "lower_bound_usd": lower_bound,
            "upper_bound_usd": upper_bound,
            "confidence_interval": 0.3,
        }


def get_cost_predictor() -> CostPredictor:
    """
    Get cost predictor instance.

    Returns:
        CostPredictor
    """
    return CostPredictor()
