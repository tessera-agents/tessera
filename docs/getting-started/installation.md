# Installation

Tessera is distributed as a Python package and can be run directly with `uvx` (recommended) or installed globally.

---

## Requirements

- **Python**: 3.13 or higher
- **uv**: Package manager (recommended)
- **API Keys**: OpenAI, Anthropic, or compatible provider

---

## Installation Methods

Tessera is published to PyPI as `tessera-agents`. You can either run it directly with `uvx` or install it globally.

### Option 1: Run Directly (Recommended)

Use `uvx` to run Tessera without installation:

```bash
uvx tessera-agents init
uvx tessera-agents main "Build a FastAPI app"
```

**Benefits:**
- No installation needed
- Always uses latest version
- Isolated execution environment

**Note:** When using `uvx`, you must include `tessera-agents` in the command (e.g., `uvx tessera-agents <command>`).

---

### Option 2: Global Installation

Install once, then use the shorter `tessera` command:

```bash
# Install the package
uv tool install tessera-agents

# Now use the 'tessera' command directly
tessera init
tessera main "Build a FastAPI app"
```

**Benefits:**
- Shorter commands after installation
- Faster execution (no download each time)
- Works offline after installation

**Note:** The PyPI package name is `tessera-agents`, but after installation, you use the `tessera` command.

---

## What Gets Created

Both installation methods create the same configuration:

```
~/.config/tessera/
  ├── config.yaml           # Main configuration
  └── prompts/              # Agent system prompts
      ├── supervisor.md
      └── ...

~/.cache/tessera/
  ├── metrics.db            # Task history and costs
  └── otel/
      └── traces.jsonl      # LLM call traces
```

---

## Configuration

On first run, Tessera creates:

```
~/.config/tessera/
  ├── config.yaml           # Main configuration
  └── prompts/              # Agent system prompts
      ├── supervisor.md
      └── ...

~/.cache/tessera/
  ├── metrics.db            # Task history and costs
  └── otel/
      └── traces.jsonl      # LLM call traces
```

---

## API Keys

Tessera needs LLM API keys. Set them via environment variables:

```bash
# Option 1: .env file (in your project directory)
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# Option 2: Export directly
export OPENAI_API_KEY=sk-your-key-here
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

## Verify Installation

```bash
tessera version
```

Expected output:
```
Tessera v0.1.0
Multi-Agent Orchestration Framework
```

---

## Next Steps

- [Quick Start Tutorial](quickstart.md)
- [Configuration Guide](../user-guide/configuration.md)
- [Define Your First Agent](../user-guide/agents.md)
