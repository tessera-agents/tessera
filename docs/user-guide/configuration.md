# Configuration

Tessera uses a single unified configuration file with multiple sections.

---

## Configuration File Location

```
~/.config/tessera/config.yaml
```

Override with:
```bash
tessera --config /path/to/custom/config.yaml
```

---

## Configuration Precedence

Settings are loaded with the following precedence (highest to lowest):

1. **CLI arguments**: `--agent supervisor`
2. **Environment variables**: `TESSERA_LOG_LEVEL=DEBUG`
3. **.env file**: `TESSERA_LOG_LEVEL=DEBUG`
4. **YAML config files**: `~/.config/tessera/config.yaml`
5. **Default values**: Built-in defaults

---

## Complete Configuration Example

```yaml
# ~/.config/tessera/config.yaml

# General Settings
tessera:
  log_level: "INFO"
  debug: false
  interactive_mode: true

# Agent Definitions
agents:
  defaults:
    temperature: 0.7
    timeout: 90
    context_size: 8192

  definitions:
    - name: "supervisor"
      model: "gpt-4"
      provider: "openai"
      system_prompt_file: "~/.config/tessera/prompts/supervisor.md"
      temperature: 0.3

    - name: "code-reviewer"
      model: "claude-3-sonnet"
      provider: "anthropic"
      system_prompt_file: "~/.config/tessera/prompts/code-reviewer.md"

# Tool Configuration
tools:
  global:
    strategy: "risk-based"
    max_risk_level: "high"

  builtin:
    filesystem:
      enabled: true
      approval_required: ["write_file", "delete_file"]

# Cost Limits
cost:
  limits:
    global:
      daily_usd: 10.00
      enforcement: "soft"

    per_task:
      max_usd: 5.00
      enforcement: "hard"

# Project Generation Phases
project_generation:
  phases:
    - name: "research"
      agents: ["researcher"]
    - name: "implementation"
      agents: ["python-expert"]
      parallel: true
    - name: "testing"
      agents: ["test-engineer"]
      min_coverage: 80
```

---

## Configuration Sections

### General Settings

```yaml
tessera:
  log_level: "INFO"      # DEBUG, INFO, WARNING, ERROR
  debug: false           # Enable debug mode
  interactive_mode: true # Use interactive prompts
  default_complexity: "medium"  # simple, medium, complex
```

### Agents

See [Agent Configuration Guide](agents.md) for details.

### Tools

See [Tools & Plugins Guide](tools.md) for details.

### Cost Management

Configure cost tracking and budget limits in the configuration file.

---

## Environment Variables

All configuration can be overridden with environment variables:

```bash
# General
export TESSERA_LOG_LEVEL=DEBUG
export TESSERA_DEBUG=true

# Nested config (use __ separator)
export TESSERA_COST__LIMITS__GLOBAL__DAILY_USD=20.00

# API Keys (recommended method)
export OPENAI_API_KEY=sk-your-key
export ANTHROPIC_API_KEY=sk-ant-your-key
```

---

## Next Steps

- [Agent Configuration](agents.md)
- [Tools & Plugins](tools.md)
- [Multi-Agent Execution](multi-agent.md)
