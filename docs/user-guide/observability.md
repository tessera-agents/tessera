# Observability & Metrics

Tessera provides comprehensive observability for all agent executions using OpenTelemetry and SQLite.

---

## Overview

All agent activity is tracked:

- **Token Usage**: Exact token counts from LLM providers
- **Cost Calculation**: Real-time cost tracking per task and agent
- **Execution Traces**: OpenTelemetry spans for all operations
- **Performance Metrics**: Agent success rates and durations
- **SQLite Storage**: Local metrics database (100% privacy)

---

## Metrics Storage

### Location

```bash
~/.local/share/tessera/metrics.db
```

### Schema

**task_assignments**
- task_id, description, type, agent_name
- assigned_at, started_at, completed_at
- status, result_summary, error_message

**agent_performance**
- agent_name, task_id, phase
- success, duration_seconds, cost_usd
- quality_score, timestamp

**model_pricing**
- provider, model_name, model_pattern
- prompt_price_per_1k, completion_price_per_1k
- effective_date, deprecated_date

---

## Token Tracking

Real token extraction from LLM responses:

```python
from tessera.observability import TokenUsageCallback

callback = TokenUsageCallback()

# Automatically captures:
- prompt_tokens: 1,234
- completion_tokens: 567
- total_tokens: 1,801
```

### Supported Providers

- ✅ **OpenAI**: Direct from API response
- ✅ **Anthropic**: Via Vertex AI metadata
- ✅ **GitHub Copilot**: Via proxy response headers
- ✅ **LiteLLM**: Unified token extraction

---

## Cost Calculation

Automatic cost tracking with provider pricing:

```python
from tessera.observability import CostCalculator

calc = CostCalculator()
cost = calc.calculate_cost(
    prompt_tokens=1000,
    completion_tokens=500,
    model="gpt-4",
    provider="openai"
)
# Returns: 0.0225  # $0.0225
```

### Pricing Table

Built-in pricing for popular models:

| Model | Provider | Prompt (per 1k) | Completion (per 1k) |
|-------|----------|----------------|---------------------|
| gpt-4 | OpenAI | $0.03 | $0.06 |
| gpt-4o | OpenAI | $0.005 | $0.015 |
| claude-sonnet-4 | Anthropic | $0.003 | $0.015 |
| gpt-4 (Copilot) | GitHub | $0.00 | $0.00 |

Custom pricing can be added via API.

---

## OpenTelemetry Tracing

Export execution traces to JSONL:

```yaml
# config.yaml
observability:
  local:
    enabled: true
    traces_file: "~/.local/share/tessera/traces.jsonl"
```

### Trace Structure

```json
{
  "trace_id": "abc123",
  "span_id": "def456",
  "name": "execute_task",
  "attributes": {
    "agent_name": "python-expert",
    "task_id": "task_001",
    "phase": "implementation"
  },
  "duration_ms": 45231
}
```

---

## Querying Metrics

### Via SQL

```bash
sqlite3 ~/.local/share/tessera/metrics.db

SELECT agent_name, COUNT(*) as tasks,
       SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes
FROM agent_performance
GROUP BY agent_name;
```

### Via Python API

```python
from tessera.observability import MetricsStore

store = MetricsStore()

# Query via internals (API coming in v1.1)
```

---

## Privacy

**100% Local**: All metrics stay on your machine

- ❌ No cloud services
- ❌ No phone-home telemetry
- ❌ No data sharing
- ✅ Pure local SQLite storage
- ✅ Pure local OTEL export

---

## Cost Limits

Set spending limits in config:

```yaml
cost:
  limits:
    global:
      daily_usd: 10.00      # Max $10/day
      enforcement: "soft"    # Warn or hard-stop

    per_task:
      max_usd: 2.00         # Max $2 per task
      enforcement: "hard"    # Reject if exceeded
```

---

## Monitoring Tools

### Real-Time

```bash
# Watch traces (live tail)
tail -f ~/.local/share/tessera/traces.jsonl | jq

# Monitor costs
watch "sqlite3 ~/.local/share/tessera/metrics.db 'SELECT SUM(cost_usd) FROM agent_performance'"
```

### Analysis

```bash
# Agent performance report
sqlite3 ~/.local/share/tessera/metrics.db <<SQL
SELECT
    agent_name,
    COUNT(*) as total_tasks,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
    ROUND(AVG(duration_seconds), 2) as avg_duration,
    ROUND(SUM(cost_usd), 4) as total_cost
FROM agent_performance
GROUP BY agent_name
ORDER BY total_cost DESC;
SQL
```

---

## Integration with Quality Monitor

```python
from tessera.workflow import QualityMonitor

monitor = QualityMonitor()

# Record iteration
monitor.record_iteration(
    iteration=1,
    coverage=75.0,
    quality_score=0.85,
    tasks_completed=5
)

# Check if should continue
should_continue, reason = monitor.should_continue(iteration=5)
```

---

## Next Steps

- [Multi-Agent Execution](multi-agent.md)
- [Configuration Guide](configuration.md)
- [Cost Management](configuration.md#cost-management)
