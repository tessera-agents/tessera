# Changelog

All notable changes to Tessera will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-11-22

### Added

**Core Features**
- True async parallel execution using asyncio with semaphore-based concurrency control
- Quality monitoring with loop detection and iteration control
- Phase-aware task execution with sub-phase application
- Comprehensive OpenTelemetry tracing with local JSONL export
- Real-time progress tracking for multi-agent execution

**Code Quality**
- Complete ruff linting with ALL rules enabled (1789 violations auto-fixed)
- Type safety improvements with mypy integration
- Structured logging infrastructure with configurable log levels
- 405 comprehensive tests (was 337)
- 79% test coverage (was 78%)

**Documentation**
- Multi-agent execution guide with parallelism examples
- Observability and metrics documentation
- Comprehensive troubleshooting guide
- Updated all user guides

**Development**
- pytest-asyncio support for async test execution
- Type stubs for PyYAML and requests
- Pragmatic ruff configuration with 30+ ignored rules
- Prevents pytest runaway via PYTEST_CURRENT_TEST detection

### Changed

**Breaking Changes**
- MultiAgentExecutor now uses true async execution (was sequential stub)
- TaskQueue.mark_failed now sets completed_at timestamp
- Mypy config moved from strict=true to pragmatic configuration

**Improvements**
- Task dependencies properly resolved before parallel execution
- Deadlock detection for circular dependencies
- Agent performance tracking with success rates
- Better error messages and logging throughout

### Fixed
- SQLite datetime deprecation warnings (Python 3.12+)
- Missing Path import in CLI tests
- Mock behaviors in configuration tests
- Slack approval test environment isolation
- Type annotation errors (lowercase `any` -> `Any`)
- 6 failing tests + 1 error resolved

### Security
- Added `check=False` to all subprocess.run calls (ruff requirement)
- Proper exception handling in async tasks
- No blind except clauses without logging

---

## [0.1.0] - 2025-11-21

### Added

**Initial Release**
- CLI with interactive mode (init, main, version commands)
- Multi-provider LLM support (OpenAI, Vertex AI, 100+ via LiteLLM)
- Real token tracking and cost calculation
- Pure OpenTelemetry observability (100% local)
- Phase-based workflow system
- Enhanced Slack integration (multi-channel, agent identities)
- 1Password secret management
- Comprehensive test suite (337 tests, 78% coverage)

**Features**
- Single unified YAML configuration
- XDG Base Directory compliance
- Task decomposition via supervisor agent
- Multi-agent foundation (task queue, agent pool)
- SQLite metrics storage
- Published documentation at https://tessera.readthedocs.io

**Tested Providers**
- GitHub Copilot (GPT-4o)
- Google Vertex AI (Claude Sonnet 4.5)

---

## [Unreleased]

### Planned for v0.4.0
- Real-time progress display in CLI
- HTTP API for remote execution
- Agent capability matching and delegation
- Workflow template system

### Planned for v1.0.0
- Session management (attach/detach)
- Plugin system with MCP integration
- Background execution mode
- Workflow DAG visualization

---

[0.3.0]: https://github.com/tessera-agents/tessera/compare/v0.1.0...v0.3.0
[0.1.0]: https://github.com/tessera-agents/tessera/releases/tag/v0.1.0
