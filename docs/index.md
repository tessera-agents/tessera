<p align="center">
  <img src="../assets/imgs/logos/logo-animated.svg" alt="Tessera Logo" width="400"/>
</p>

# Tessera

**No-code multi-agent AI orchestration for full project generation.**

Like mosaic tiles coming together to form a complete picture, Tessera coordinates specialized AI agents to build entire software projects from scratch.

---

## What is Tessera?

Tessera is a multi-agent AI orchestration framework for automated project generation.

**Features:**
- Multi-agent coordination (supervisor, interviewer, specialist agents)
- Multi-provider LLM support (OpenAI, Vertex AI, 100+ via LiteLLM)
- Persistent memory system for agent learning
- Workspace management with sandboxing
- Real token tracking and cost calculation
- Complete local observability (OpenTelemetry + SQLite)
- Extensible tool system with MCP support

**No coding required** - define agents with markdown prompts.

---

## Key Features

### 🎯 **No-Code Operation**
Define agents using markdown system prompts. No Python coding required.

### 🤝 **Multi-Agent Coordination**
- **Supervisor**: Orchestrates task decomposition and delegation
- **Interviewer**: Evaluates agents and gathers requirements
- **Specialists**: Code reviewers, testers, security experts, and more

### 🚀 **Parallel Execution**
Run multiple agents concurrently with intelligent coordination and conflict resolution.

### 🔍 **Full Observability**
- OpenTelemetry tracing (local JSONL files)
- SQLite metrics (task history, costs, performance)
- Real-time cost tracking
- Agent performance analytics

### 🛠️ **Extensible Tools**
- **Built-in**: File operations, Git, web search, code execution
- **Plugins**: Add custom tools via Python files
- **MCP**: Integrate Model Context Protocol servers

### 💰 **Cost Management**
- Automatic cost calculation for 100+ LLM models
- Configurable budget limits (daily, per-task, per-agent)
- Cost threshold approvals

### 🧠 **Persistent Memory**
- Long-term conversation history across sessions
- Agent learnings and decisions storage
- Vector-based semantic search
- SQLite-backed persistence

### 📁 **Workspace Management**
- Project isolation and tracking
- Sandboxing with resource limits
- Filesystem protection
- Archive and restore capabilities

### 🔒 **Security First**
- Configurable sandboxing (Docker, Podman, uv)
- Risk-based approval gates
- File locking for conflict prevention

### 📊 **Intelligent Agent Selection**
- Performance-based routing
- Adaptive learning from failures
- Interview-driven capability assessment

---

## Quick Start

### Installation

```bash
# Option 1: Run directly with uvx
uvx tessera-agents init

# Option 2: Install globally, then use 'tessera' command
uv tool install tessera-agents
tessera init
```

This creates:
- `~/.config/tessera/config.yaml` - Your configuration
- `~/.config/tessera/prompts/` - Agent system prompts

**Note:** Examples below use `tessera` commands (assumes global install). With `uvx`, use `uvx tessera-agents <command>`.

### First Project

```bash
tessera
```

The interactive wizard will:
1. Ask about your project
2. Interview you for requirements
3. Generate a comprehensive plan
4. Execute with multiple agents in parallel
5. Deliver a complete, tested, documented project

---

## Example

```bash
$ tessera

? What would you like to build?
> A FastAPI backend with user authentication, PostgreSQL database,
> and comprehensive tests.

? Complexity: Complex
? Interview mode: Yes

[Interviewer asks 8 questions about requirements...]

✓ Plan generated: 32 tasks across 7 phases
✓ Estimated cost: $8.50 | Time: 6-8 hours

? Approve execution? Yes

[Shows live progress with parallel agents...]

✓ Project complete: ./generated_project/
  - 45 files created
  - 89% test coverage
  - Security audit passed
  - Documentation generated
```

---

## Architecture

Tessera uses:

- **LangGraph**: Complex multi-agent workflow orchestration
- **Pydantic AI**: Type-safe agent definitions
- **LiteLLM**: Unified interface to 100+ LLM providers
- **OpenTelemetry**: Vendor-neutral observability
- **SQLite**: Local metrics and state persistence

---

## Use Cases

### For Solo Developers
- Generate MVPs quickly
- Explore new tech stacks
- Automate boilerplate projects
- Learn through AI-generated examples

### For Teams
- Rapid prototyping
- Code review automation
- Documentation generation
- Security audits

---

## Next Steps

- [Installation Guide](getting-started/installation.md)
- [Quick Start Tutorial](getting-started/quickstart.md)
- [Configuration Guide](user-guide/configuration.md)
- [Memory System](user-guide/memory.md)
- [Workspace Management](user-guide/workspace.md)

---

## License

MIT License - See LICENSE file for details.
