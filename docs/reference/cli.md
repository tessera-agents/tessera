# CLI Reference

Complete reference for all Tessera CLI commands.

---

## Main Command

### `tessera [TASK]`

Run Tessera in interactive mode or with a direct task.

**Usage:**
```bash
# Interactive mode
tessera

# Direct task
tessera "Build a web scraper"

# With options
tessera --dry-run "Deploy application"
tessera --background "Generate project"
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--dry-run` | | Show plan without executing |
| `--background` | `-b` | Run in background mode |
| `--config` | `-c` | Custom config file path |

---

## Configuration Commands

### `tessera init`

Initialize Tessera configuration with interactive wizard.

**Usage:**
```bash
tessera init
```

Creates:
- `~/.config/tessera/config.yaml`
- `~/.config/tessera/prompts/supervisor.md`
- `~/.cache/tessera/metrics.db`

---

### `tessera config show`

Display current configuration.

**Usage:**
```bash
tessera config show
tessera config show --section agents
```

---

### `tessera config validate`

Validate configuration file syntax and schema.

**Usage:**
```bash
tessera config validate
```

---

## Session Management

### `tessera status <SESSION_ID>`

Check status of a running or completed session.

**Usage:**
```bash
tessera status sess-20251116-abc123
```

---

### `tessera attach <SESSION_ID>`

Attach to a running session (shows live progress).

**Usage:**
```bash
tessera attach sess-20251116-abc123
```

Press `Ctrl+B D` to detach (tmux-style).

---

### `tessera pause <SESSION_ID>`

Pause a running session.

**Usage:**
```bash
tessera pause sess-20251116-abc123
```

---

### `tessera resume <SESSION_ID>`

Resume a paused session.

**Usage:**
```bash
tessera resume sess-20251116-abc123
```

---

### `tessera list`

List all sessions (active and recent).

**Usage:**
```bash
tessera list
tessera list --active  # Only running sessions
tessera list --all     # Include completed sessions
```

---

## Metrics & Observability

### `tessera metrics show`

Display metrics and analytics.

**Usage:**
```bash
# Overall metrics
tessera metrics show

# Agent-specific
tessera metrics show --agent code-reviewer

# Date range
tessera metrics show --date-range last-7-days
```

---

### `tessera cost summary`

Show cost breakdown and budget status.

**Usage:**
```bash
tessera cost summary
tessera cost summary --agent supervisor
tessera cost summary --month 2025-11
```

---

### `tessera trace view <TASK_ID>`

View OTEL trace for a specific task.

**Usage:**
```bash
tessera trace view task-123
```

---

## Agent Management

### `tessera agent list`

List all configured agents.

**Usage:**
```bash
tessera agent list
```

---

### `tessera agent test <AGENT_NAME>`

Test an agent with a sample task.

**Usage:**
```bash
tessera agent test code-reviewer
```

---

## Utility Commands

### `tessera version`

Show Tessera version.

**Usage:**
```bash
tessera version
```

---

### `tessera doctor`

Check system health and configuration.

**Usage:**
```bash
tessera doctor
```

Validates:
- Configuration file syntax
- API key availability
- Directory permissions
- Database integrity

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TESSERA_CONFIG_DIR` | Override config directory | `/custom/path` |
| `TESSERA_CACHE_DIR` | Override cache directory | `/custom/cache` |
| `TESSERA_LOG_LEVEL` | Set log level | `DEBUG` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | API error |
| 4 | Budget exceeded |
| 130 | Interrupted by user (Ctrl+C) |

---

## Examples

### Generate a Web Application
```bash
tessera "Build a FastAPI REST API with user authentication"
```

### Generate with Custom Config
```bash
tessera --config ./project-config.yaml "Build microservice"
```

### Dry Run (Plan Only)
```bash
tessera --dry-run "Deploy to production"
```

### Background Mode
```bash
tessera --background "Generate full-stack application"
# Returns: Session ID: sess-20251116-abc123
tessera attach sess-20251116-abc123
```

---

## Next Steps

- [Configuration Guide](../user-guide/configuration.md)
- [Agent System](../user-guide/agents.md)
- [Multi-Agent Execution](../user-guide/multi-agent.md)
