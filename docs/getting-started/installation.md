# Installation

Tessera is distributed as a Python package and can be run directly with `uvx` (recommended) or installed globally.

---

## Requirements

- **Python**: 3.13 or higher
- **uv**: Package manager (recommended)
- **API Keys**: OpenAI, Anthropic, or compatible provider

---

## Quick Install (Recommended)

Use `uvx` to run Tessera without installation:

```bash
uvx tessera init
```

This command:
1. Downloads Tessera automatically
2. Creates configuration directory (`~/.config/tessera/`)
3. Launches interactive setup wizard

---

## Global Installation

**Note:** Tessera is not yet published to PyPI. For now, install from source:

```bash
git clone https://github.com/wgordon17/tessera.git
cd tessera
uv sync
uv run tessera init
```

Once published to PyPI, you'll be able to:
```bash
uv tool install tessera
tessera init
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
