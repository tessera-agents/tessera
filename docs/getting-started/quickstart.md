# Quick Start

This tutorial walks you through using Tessera to generate your first project in under 10 minutes.

---

## Installation

Choose your preferred method:

```bash
# Option 1: Run directly with uvx
uvx tessera-agents init

# Option 2: Install globally, then use shorter commands
uv tool install tessera-agents
```

**For the rest of this guide**, we'll use `tessera` commands (assumes you've installed globally). If using `uvx`, replace `tessera` with `uvx tessera-agents`.

---

## Step 1: Initialize Configuration

Run the interactive setup wizard:

```bash
tessera init
```

The wizard will ask:
- Which LLM provider to use (OpenAI, Anthropic, etc.)
- Your API key
- Default agent configuration

This creates `~/.config/tessera/config.yaml`.

---

## Step 2: Generate Your First Project

Start Tessera in interactive mode:

```bash
tessera
```

### Interactive Prompts

```
? What would you like to build?
> A simple Python CLI tool that fetches weather data

? Complexity level: Simple

? Interview mode (recommended for better results)?
> Yes
```

### Interview Phase

The Interviewer agent will ask clarifying questions:

```
Q1/5: Which weather API should we use?
> OpenWeatherMap

Q2/5: What data should be displayed?
> Current temperature, conditions, and 5-day forecast

Q3/5: How should users provide location?
> City name as command-line argument

...
```

### Planning Phase

The Supervisor agent generates a comprehensive plan:

```
✓ Plan generated: 8 tasks across 5 phases
✓ Agents required: 4 (code-architect, python-expert, test-engineer, tech-writer)
✓ Estimated cost: $1.20 | Time: ~45 minutes

Tasks:
  1. Design CLI architecture
  2. Implement weather API client
  3. Create command-line interface
  4. Add error handling
  5. Write unit tests
  6. Write integration tests
  7. Create README documentation
  8. Generate usage examples

? Approve this plan? [Y/n]:
```

### Execution Phase

```
Starting execution...

Progress: ██████░░░░░░ 50% (4/8 tasks) | Cost: $0.62

ACTIVE AGENTS (2/3):
  ● python-expert     [T2] Weather API client (3m)
  ● test-engineer     [T5] Unit tests (1m)

COMPLETED:
  ✓ T1  CLI architecture design      2m12s  $0.08
  ✓ T3  Command-line interface      5m32s  $0.24

[Press 'P' to pause | 'Q' to quit]
```

### Completion

```
✓ Project generation complete!

Generated:./weather-cli/
  ├── src/
  │   ├── __init__.py
  │   ├── client.py
  │   └── cli.py
  ├── tests/
  │   ├── test_client.py
  │   └── test_cli.py
  ├── README.md
  ├── pyproject.toml
  └── .gitignore

Summary:
  - 8 files created
  - 245 lines of code
  - 92% test coverage
  - All tests passing ✓
  - Documentation complete ✓

Total cost: $1.18 | Duration: 42m

? Open project directory? [Y/n]:
```

---

## Step 3: Review the Generated Project

```bash
cd weather-cli
cat README.md
```

The README will include:
- Project description
- Installation instructions
- Usage examples
- API documentation
- Development guide

---

## Step 4: Run the Generated Project

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Use the CLI
uv run python -m src.cli "San Francisco"
```

---

## Next Steps

### Customize Agents

Edit `~/.config/tessera/prompts/python-expert.md` to customize how the agent writes code.

### Adjust Configuration

Edit `~/.config/tessera/config.yaml` to:
- Add more agents
- Configure cost limits
- Enable tools and plugins
- Set up Slack notifications

### Generate Another Project

```bash
uvx tessera "Build a REST API with FastAPI and PostgreSQL"
```

---

## Learn More

- [Configuration Guide](../user-guide/configuration.md)
- [Agent System](../user-guide/agents.md)
- [Interactive Mode](../user-guide/interactive-mode.md)
- [Background Execution](../user-guide/background-mode.md)
