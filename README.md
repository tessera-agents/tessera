# Tessera

**No-code multi-agent AI orchestration for full project generation.**

Like mosaic tiles forming a complete picture, Tessera coordinates specialized AI agents to build entire software projects from simple descriptions.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)

---

## What is Tessera?

Tessera orchestrates multiple AI agents working together to generate complete, tested, documented software projects. Each agent is a specialist (coding, testing, review, documentation) that contributes its expertise to the final result.

**Key Features:**
- **No-code operation** - Define agents with markdown prompts
- **Multi-agent coordination** - Parallel execution with dependency management
- **100% local-first** - All data stays on your machine
- **Multi-provider** - Works with OpenAI, Anthropic, Vertex AI, and 100+ LLM providers
- **Comprehensive observability** - OpenTelemetry traces and SQLite metrics
- **Cost tracking** - Automatic token and cost calculation

---

## Quick Start

### Installation

```bash
# Option 1: Run directly with uvx (recommended)
uvx tessera-agents init

# Option 2: Install globally, then use 'tessera' command
uv tool install tessera-agents
tessera init
```

### First Project

```bash
tessera main "Build a FastAPI REST API with user authentication"
```

**Current (v0.1.0):** Supervisor decomposes task into subtasks
**Planned (v0.2.0+):** Full multi-agent execution with:
1. User interview for requirements
2. Research best practices
3. Architecture design
4. Project generation
5. Parallel agent implementation
6. Testing, review, and documentation

---

## Configuration

Tessera uses a single unified configuration file:

```yaml
# ~/.config/tessera/config.yaml

agents:
  definitions:
    - name: "supervisor"
      model: "gpt-4"
      provider: "openai"
      system_prompt_file: "~/.config/tessera/prompts/supervisor.md"

    - name: "python-expert"
      model: "gpt-4o"
      provider: "openai"
      capabilities: ["python", "coding"]

cost:
  limits:
    per_task:
      max_usd: 5.00
```

See [Configuration Guide](docs/user-guide/configuration.md) for details.

---

## Supported Providers

Tessera works with 100+ LLM providers via LiteLLM:

- **OpenAI** - Direct or via GitHub Copilot proxy
- **Anthropic** - Claude via Vertex AI or direct API
- **Google** - Gemini, Vertex AI
- **Azure** - Azure OpenAI
- **Local** - Ollama, LM Studio
- **And many more**

---

## Architecture

### Core Components

- **CLI** - Interactive interface with Typer and Rich
- **Config** - Unified YAML with Pydantic validation
- **Workflow** - Phase-based execution with sub-phases
- **Agents** - Specialized AI agents with capabilities
- **Observability** - OpenTelemetry + SQLite (100% local)
- **Cost Tracking** - Automatic calculation for all providers

### Workflow Phases

1. **User Interview** - Gather requirements
2. **Research** - Best practices and technology evaluation
3. **Architecture** - System design and planning
4. **Project Generation** - Scaffolding and setup
5. **Execution** - Implementation with testing, review, docs

Each phase can have sub-phases that apply to all tasks (deliverables, checklists, subtasks).

---

## Examples

See [examples/](examples/) for:
- Basic supervisor usage
- Interviewer evaluation
- Panel system demos
- Slack approval workflows
- Copilot proxy integration
- 1Password secret management

---

## Development

```bash
# Clone repository
git clone https://github.com/wgordon17/tessera.git
cd tessera

# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Build documentation
uv run mkdocs serve
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for commit guidelines and development workflow.

---

## Project Status

**v0.1.0** - Foundation Complete ✅
- Single-agent execution
- Real token tracking
- Multi-provider support
- Complete observability

**v0.2.0** - Multi-Agent (60% complete)
- Task queue and agent pool implemented
- CLI integration ready
- Needs: Real task execution

**v0.3.0+** - Planned
- Parallel execution
- Reusable workflows
- Enhanced Slack integration

---

## License

MIT License - See LICENSE file for details.

---

## Links

- **Documentation:** [User Guide](docs/)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Issues:** [GitHub Issues](https://github.com/tessera-agents/tessera/issues)
- **Organization:** [tessera-agents](https://github.com/tessera-agents)
