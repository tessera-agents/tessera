"""
Pure OpenTelemetry tracing for Tessera - 100% local, zero cloud dependencies.

Provides local-first LLM call tracing using standard OpenTelemetry with NO external services.
"""

import json
import os
from pathlib import Path

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from tessera.config.xdg import get_tessera_cache_dir

# Global tracer instance
_tracer: trace.Tracer | None = None
_initialized: bool = False


class FileSpanExporter:
    """
    Simple JSONL file exporter for OpenTelemetry spans.

    100% local - no network calls, no cloud services.
    """

    def __init__(self, file_path: Path) -> None:
        """
        Initialize file exporter.

        Args:
            file_path: Path to JSONL file for traces
        """
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def export(self, spans: list) -> None:
        """Export spans to JSONL file."""
        with Path(self.file_path).open("a") as f:
            for span in spans:
                # Convert span to dict
                span_dict = {
                    "trace_id": format(span.context.trace_id, "032x"),
                    "span_id": format(span.context.span_id, "016x"),
                    "name": span.name,
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "attributes": dict(span.attributes) if span.attributes else {},
                    "events": [
                        {"name": e.name, "timestamp": e.timestamp, "attributes": dict(e.attributes)}
                        for e in span.events
                    ]
                    if span.events
                    else [],
                    "status": {
                        "status_code": span.status.status_code.name,
                        "description": span.status.description,
                    },
                }
                f.write(json.dumps(span_dict) + "\n")

    def shutdown(self) -> None:
        """Shutdown exporter."""

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any pending spans."""
        return True


def init_tracer(
    app_name: str = "tessera",
    export_to_file: bool = True,
    file_path: Path | None = None,
) -> trace.Tracer:
    """
    Initialize pure OpenTelemetry tracer - 100% local, zero cloud dependencies.

    Args:
        app_name: Application name for traces
        export_to_file: Whether to export traces to JSONL file
        file_path: Custom file path (default: ~/.cache/tessera/otel/traces.jsonl)

    Returns:
        Configured OpenTelemetry tracer

    Example:
        >>> from tessera.observability import init_tracer, get_tracer
        >>> init_tracer()
        >>> tracer = get_tracer()
        >>> with tracer.start_as_current_span("my_task"):
        ...     # Your code here - span auto-tracked
        ...     result = llm.invoke("Hello")
    """
    global _tracer, _initialized

    if _initialized:
        return _tracer  # type: ignore[return-value]

    # Create resource with app metadata
    resource = Resource.create(
        {
            "service.name": app_name,
            "service.version": "0.1.0",
            "deployment.environment": os.getenv("ENV", "development"),
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add file exporter if requested
    if export_to_file:
        if file_path is None:
            file_path = get_tessera_cache_dir() / "otel" / "traces.jsonl"

        file_exporter = FileSpanExporter(file_path)
        provider.add_span_processor(SimpleSpanProcessor(file_exporter))  # type: ignore[arg-type]

    # Set as global provider
    trace.set_tracer_provider(provider)

    # Get the tracer
    _tracer = trace.get_tracer(app_name)
    _initialized = True

    return _tracer


def get_tracer() -> trace.Tracer:
    """
    Get the global OpenTelemetry tracer.

    Initializes tracer if not already initialized.

    Returns:
        OpenTelemetry tracer instance
    """
    global _tracer, _initialized

    if not _initialized:
        _tracer = init_tracer()

    return _tracer  # type: ignore[return-value]


def set_span_attributes(
    agent_name: str | None = None,
    task_id: str | None = None,
    task_type: str | None = None,
    phase: str | None = None,
    **custom_attributes: object,
) -> None:
    """
    Set custom attributes on the current span.

    Args:
        agent_name: Name of the agent executing the task
        task_id: Unique task identifier
        task_type: Type of task being executed
        phase: SDLC phase (research, implementation, etc.)
        **custom_attributes: Additional custom attributes

    Example:
        >>> with tracer.start_as_current_span("agent_task"):
        ...     set_span_attributes(
        ...         agent_name="code-reviewer",
        ...         task_id="task-123",
        ...         phase="review"
        ...     )
    """
    span = trace.get_current_span()

    if not span.is_recording():
        return

    # Set standard Tessera attributes
    if agent_name:
        span.set_attribute("agent.name", agent_name)
    if task_id:
        span.set_attribute("task.id", task_id)
    if task_type:
        span.set_attribute("task.type", task_type)
    if phase:
        span.set_attribute("project.phase", phase)

    # Set custom attributes
    for key, value in custom_attributes.items():
        span.set_attribute(key, str(value))
