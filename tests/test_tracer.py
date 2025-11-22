"""
Tests for OTEL tracer.
"""

import pytest
from pathlib import Path
import tempfile

from tessera.observability import init_tracer, get_tracer
from tessera.observability.tracer import set_span_attributes, FileSpanExporter


@pytest.mark.unit
class TestFileSpanExporter:
    """Test file span exporter."""

    def test_export_writes_jsonl(self):
        """Test exporter writes to JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "traces.jsonl"
            exporter = FileSpanExporter(file_path)

            # Create mock span
            mock_span = Mock()
            mock_span.context = Mock(trace_id=123, span_id=456)
            mock_span.name = "test_span"
            mock_span.start_time = 1000
            mock_span.end_time = 2000
            mock_span.attributes = {"key": "value"}
            mock_span.events = []
            mock_span.status = Mock(status_code=Mock(name="OK"), description=None)

            exporter.export([mock_span])

            # Verify file was written
            assert file_path.exists()
            content = file_path.read_text()
            assert "test_span" in content

    def test_shutdown(self):
        """Test exporter shutdown."""
        exporter = FileSpanExporter(Path("/tmp/test"))
        exporter.shutdown()  # Should not error

    def test_force_flush(self):
        """Test force flush."""
        exporter = FileSpanExporter(Path("/tmp/test"))
        result = exporter.force_flush()
        assert result is True


@pytest.mark.unit
class TestTracer:
    """Test tracer initialization."""

    def test_init_tracer_creates_tracer(self):
        """Test tracer initialization."""
        tracer = init_tracer(app_name="test", export_to_file=False)
        assert tracer is not None

    def test_get_tracer_returns_same_instance(self):
        """Test get_tracer returns singleton."""
        tracer1 = get_tracer()
        tracer2 = get_tracer()
        assert tracer1 is tracer2

    def test_set_span_attributes(self):
        """Test setting span attributes."""
        # Just verify it doesn't error
        set_span_attributes(
            agent_name="test",
            task_id="task-1",
            task_type="test"
        )
        # Attributes set on non-recording span won't error


from unittest.mock import Mock
