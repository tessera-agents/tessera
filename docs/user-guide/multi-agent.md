# Multi-Agent Execution

Tessera v1.0.0 supports true parallel multi-agent execution using asyncio for concurrent task processing.

---

## Overview

Multi-agent execution allows multiple AI agents to work on different tasks simultaneously:

- **Parallel Processing**: Tasks execute concurrently up to `max_parallel` limit
- **Dependency Management**: Tasks wait for dependencies before execution
- **Intelligent Assignment**: Best agent selected based on capabilities
- **Progress Tracking**: Real-time monitoring of task status

---

## How It Works

### 1. Task Decomposition

The supervisor agent analyzes your objective and breaks it into subtasks:

```python
# Supervisor decomposes: "Build a FastAPI service"
subtasks = [
    "Design API endpoints and models",
    "Implement core business logic",
    "Add authentication middleware",
    "Write comprehensive tests",
    "Create API documentation",
]
```

### 2. Dependency Resolution

Tasks are organized with dependencies:

```python
tasks = [
    Task(id="t1", description="Design API", dependencies=[]),
    Task(id="t2", description="Implement logic", dependencies=["t1"]),
    Task(id="t3", description="Add auth", dependencies=["t2"]),
    Task(id="t4", description="Write tests", dependencies=["t2"]),
]
```

### 3. Parallel Execution

Tasks execute concurrently when dependencies are met:

```
Iteration 1: [t1] executes
Iteration 2: [t2] executes
Iteration 3: [t3, t4] execute in parallel  # Both depend on t2
```

### 4. Progress Monitoring

Track execution in real-time:

```python
progress = executor.get_progress()
# {
#   "queue": {"pending": 2, "in_progress": 2, "completed": 1},
#   "agent_pool": {"available": 1, "busy": 2},
# }
```

---

## Configuration

Enable multi-agent mode in your config:

```yaml
# config.yaml
workflow:
  max_parallel: 3  # Max concurrent agents
  max_iterations: 10  # Max execution loops

agents:
  definitions:
    - name: supervisor
      model: gpt-4
      capabilities: [orchestration]

    - name: python-expert
      model: gpt-4
      capabilities: [python, backend]

    - name: test-engineer
      model: gpt-4
      capabilities: [testing, quality]
```

---

## CLI Usage

```bash
# Standard execution (uses multi-agent if multiple agents defined)
tessera main "Build a REST API with authentication"

# Monitor progress
tessera status  # Coming in v1.1
```

---

## Quality Monitoring

Built-in quality monitoring prevents infinite loops:

- **Loop Detection**: Identical outputs detected via hashing
- **Improvement Tracking**: Coverage and quality score monitored
- **Automatic Termination**: Stops if no improvement for N iterations

```python
monitor = QualityMonitor(
    min_coverage_improvement=0.05,  # Require 5% coverage gain
    max_iterations_without_improvement=3,  # Stop if stuck
)
```

---

## Best Practices

### Agent Specialization

Define agents with specific capabilities:

```yaml
agents:
  definitions:
    - name: backend-dev
      capabilities: [python, fastapi, databases]
      model: gpt-4

    - name: frontend-dev
      capabilities: [javascript, react, css]
      model: gpt-4
```

### Task Dependencies

Supervisor automatically infers dependencies:

- API implementation depends on design
- Tests depend on implementation
- Documentation depends on completed code

### Parallelism Limits

Set `max_parallel` based on:

- **API rate limits**: Stay within provider limits
- **Cost control**: More parallel = higher concurrent cost
- **Quality**: Too much parallelism can reduce coordination

Recommended: `max_parallel: 3-5`

---

## Metrics & Observability

All multi-agent execution is tracked:

```python
# Metrics stored in SQLite
~/.local/share/tessera/metrics.db

# Includes:
- Task assignments and completions
- Agent performance and success rates
- Cost per task and agent
- Duration and iterations
```

See [Observability Guide](observability.md) for details.

---

## Next Steps

- [Observability & Metrics](observability.md)
- [Agent Configuration](agents.md)
- [Phase-Based Workflows](configuration.md)
