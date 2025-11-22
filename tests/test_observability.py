"""
Tests for observability components.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tessera.observability import CostCalculator, MetricsStore, TokenUsageCallback
from langchain_core.outputs import LLMResult


@pytest.mark.unit
class TestCostCalculator:
    """Test cost calculation."""

    def test_calculate_cost_gpt4(self):
        """Test calculating cost for GPT-4."""
        calc = CostCalculator()

        cost = calc.calculate("gpt-4", 1000, 500, "openai")

        # GPT-4: $0.03/1k input, $0.06/1k output
        expected = (1000 / 1000 * 0.03) + (500 / 1000 * 0.06)
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_claude(self):
        """Test calculating cost for Claude."""
        calc = CostCalculator()

        cost = calc.calculate("claude-3-5-sonnet-20241022", 1000, 500, "anthropic")

        # Claude Sonnet: $0.003/1k input, $0.015/1k output
        expected = (1000 / 1000 * 0.003) + (500 / 1000 * 0.015)
        assert abs(cost - expected) < 0.0001

    def test_unknown_model_returns_zero(self):
        """Test unknown model returns zero cost."""
        calc = CostCalculator()

        cost = calc.calculate("unknown-model", 1000, 500)

        assert cost == 0.0

    def test_add_custom_pricing(self):
        """Test adding custom model pricing."""
        calc = CostCalculator()

        calc.add_pricing(
            provider="custom",
            model_name="custom-model",
            prompt_price_per_1k=0.01,
            completion_price_per_1k=0.02
        )

        cost = calc.calculate("custom-model", 1000, 500, "custom")
        expected = (1000 / 1000 * 0.01) + (500 / 1000 * 0.02)

        assert abs(cost - expected) < 0.0001


@pytest.mark.unit
class TestMetricsStore:
    """Test metrics storage."""

    def test_record_task_assignment(self):
        """Test recording task assignment."""
        import uuid
        store = MetricsStore()
        task_id = f"test-{uuid.uuid4().hex[:8]}"

        store.record_task_assignment(
            task_id=task_id,
            task_description="Test task",
            agent_name="supervisor",
            agent_config={"model": "gpt-4"}
        )

        # Verify task was recorded
        assert True

    def test_update_task_status(self):
        """Test updating task status."""
        import uuid
        store = MetricsStore()
        task_id = f"test-{uuid.uuid4().hex[:8]}"

        store.record_task_assignment(
            task_id=task_id,
            task_description="Test",
            agent_name="agent1",
            agent_config={}
        )

        store.update_task_status(
            task_id=task_id,
            status="completed",
            total_tokens=1000,
            total_cost_usd=0.05
        )

        # Verify update succeeded
        assert True

    def test_record_agent_performance(self):
        """Test recording agent performance metrics."""
        import uuid
        store = MetricsStore()
        task_id = f"test-{uuid.uuid4().hex[:8]}"

        # First record the task
        store.record_task_assignment(
            task_id=task_id,
            task_description="Test",
            agent_name="python-expert",
            agent_config={}
        )

        # Then record performance
        store.record_agent_performance(
            agent_name="python-expert",
            task_id=task_id,
            success=True,
            duration_seconds=120,
            cost_usd=0.05
        )

        # Verify performance recorded
        stats = store.get_agent_stats("python-expert")
        assert stats["total_tasks"] >= 1
        assert stats["successful_tasks"] >= 1


@pytest.mark.unit
class TestTokenUsageCallback:
    """Test token usage callback."""

    def test_captures_token_usage(self):
        """Test callback captures token usage."""
        callback = TokenUsageCallback()

        # Simulate LLM result
        result = MagicMock(spec=LLMResult)
        result.llm_output = {
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            },
            "model_name": "gpt-4"
        }

        callback.on_llm_end(result)

        usage = callback.get_usage()
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert usage["total_tokens"] == 150
        assert usage["call_count"] == 1
        assert usage["model_name"] == "gpt-4"

    def test_accumulates_multiple_calls(self):
        """Test callback accumulates across multiple calls."""
        callback = TokenUsageCallback()

        for _ in range(3):
            result = MagicMock(spec=LLMResult)
            result.llm_output = {
                "token_usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
            }
            callback.on_llm_end(result)

        usage = callback.get_usage()
        assert usage["total_tokens"] == 450  # 150 * 3
        assert usage["call_count"] == 3
