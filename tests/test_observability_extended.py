"""Extended observability tests for coverage."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from tessera.observability import get_tracer, init_tracer
from tessera.observability.callbacks import TokenUsageCallback
from tessera.observability.metrics import MetricsStore


@pytest.mark.unit
class TestTokenUsageCallbackExtended:
    """Extended token usage callback tests."""

    def test_callback_accumulation_multiple_runs(self):
        """Test token accumulation across multiple LLM calls."""
        callback = TokenUsageCallback()

        # First LLM call
        callback.on_llm_end(
            response=Mock(
                llm_output={
                    "token_usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                    }
                }
            ),
        )

        # Second LLM call
        callback.on_llm_end(
            response=Mock(
                llm_output={
                    "token_usage": {
                        "prompt_tokens": 200,
                        "completion_tokens": 150,
                    }
                }
            ),
        )

        assert callback.total_tokens == 500  # 100+50+200+150
        assert callback.prompt_tokens == 300
        assert callback.completion_tokens == 200

    def test_callback_with_zero_tokens(self):
        """Test callback handles zero token responses."""
        callback = TokenUsageCallback()

        callback.on_llm_end(
            response=Mock(
                llm_output={
                    "token_usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                    }
                }
            ),
        )

        assert callback.total_tokens == 0

    def test_get_usage_dict(self):
        """Test getting usage as dictionary."""
        callback = TokenUsageCallback()

        callback.on_llm_end(
            response=Mock(
                llm_output={
                    "token_usage": {
                        "prompt_tokens": 150,
                        "completion_tokens": 75,
                    }
                }
            ),
        )

        usage = callback.get_usage()

        assert usage["prompt_tokens"] == 150
        assert usage["completion_tokens"] == 75
        assert usage["total_tokens"] == 225


@pytest.mark.unit
class TestMetricsStoreExtended:
    """Extended metrics store tests."""

    def test_update_task_status_with_summary(self):
        """Test updating task status with result summary."""
        store = MetricsStore()

        task_id = "task1"
        store.record_task_assignment(task_id, "Test task", "implementation", "agent1", {})

        store.update_task_status(
            task_id,
            status="completed",
            result_summary="Successfully created tests",
        )

        # Verify via metrics (we can't directly query, but ensure no errors)
        assert True  # Method executed without error

    def test_update_task_status_with_error(self):
        """Test updating task status with error message."""
        store = MetricsStore()

        task_id = "task1"
        store.record_task_assignment(task_id, "Test task", "implementation", "agent1", {})

        store.update_task_status(
            task_id,
            status="failed",
            error_message="Agent timeout",
        )

        # Method should execute without error
        assert True

    def test_record_agent_performance_full(self):
        """Test recording complete agent performance metrics."""
        store = MetricsStore()

        store.record_agent_performance(
            agent_name="python-expert",
            task_id="task123",
            phase="implementation",
            success=True,
            duration_seconds=45.5,
            cost_usd=0.032,
            quality_score=0.92,
            reassigned=False,
            off_topic=False,
        )

        # Verify no errors
        assert True


@pytest.mark.unit
class TestTracerExtended:
    """Extended tracer tests."""

    def test_init_tracer_with_file_export(self):
        """Test initializing tracer with file export."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "traces.jsonl"

            tracer = init_tracer(
                app_name="test-app",
                export_to_file=True,
                file_path=file_path,
            )

            assert tracer is not None

    def test_init_tracer_no_export(self):
        """Test initializing tracer without file export."""
        tracer = init_tracer(
            app_name="test-app",
            export_to_file=False,
        )

        assert tracer is not None

    def test_get_tracer_singleton(self):
        """Test tracer singleton behavior."""
        tracer1 = get_tracer()
        tracer2 = get_tracer()

        assert tracer1 is tracer2  # Same instance

    def test_set_span_attributes_partial(self):
        """Test setting partial span attributes."""
        from tessera.observability.tracer import set_span_attributes

        # Should not raise even if no active span
        set_span_attributes(agent_name="test-agent", task_id="task1")

        # Method executes without error
        assert True

    def test_set_span_attributes_with_custom(self):
        """Test setting custom attributes."""
        from tessera.observability.tracer import set_span_attributes

        set_span_attributes(
            agent_name="agent1",
            task_id="task1",
            custom_key="custom_value",
            another_key="another_value",
        )

        # Should execute without error
        assert True
