# Contributing to Tessera

## Commit Message Guidelines

Tessera follows the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **chore**: Maintenance tasks (dependencies, configs)
- **refactor**: Code refactoring
- **test**: Test additions or modifications
- **perf**: Performance improvements

### Scopes

Project-specific scopes for Tessera:

- **cli**: Command-line interface
- **config**: Configuration system
- **workflow**: Phase and task execution
- **observability**: Metrics, tracing, cost tracking
- **agents**: Agent implementations
- **tools**: Tool system and plugins
- **slack**: Slack integration
- **api**: HTTP API and sessions
- **repo**: Repository structure changes

### Examples

**Good:**
```
feat(cli): add interactive mode with user prompts

Implements guided workflow for task input with complexity
selection and interview mode option.
```

```
fix(observability): correct token extraction from LiteLLM responses

Token callback now properly captures usage metadata from
LangChain LiteLLM wrapper.
```

```
chore(deps): add google-cloud-aiplatform for Vertex AI support
```

**Bad:**
```
🎉 ADDED COOL NEW FEATURE!!! (with emojis and caps)
```

```
Updated files - Changed 50 files, 200 lines added, files:
src/foo.py, src/bar.py, ... (file listings)
```

```
chore(repo): rename PyPI package to tessera-agents

Changes:
- pyproject.toml: Update package name
- Documentation: Explain installation methods
- CLI help text updated

Benefits:
- Respects existing package community
- Clear differentiation
- Python imports unchanged

(Too verbose - lists files, explains changes, documents benefits)
```

**Better:**
```
chore(repo): rename PyPI package to tessera-agents

Package name 'tessera' conflicts with existing PyPI package.
Use 'tessera-agents' for PyPI while keeping 'tessera' as import
and CLI command name after installation.

(Concise - explains why, brief technical detail, no file listing)
```

### Guidelines

**DO:**
- Use present tense ("add feature" not "added feature")
- Be concise in description (50 chars or less)
- Use body for detailed explanation if needed
- Reference issues: "Closes #123"

**DON'T:**
- Use emojis in commit messages
- Use ALL CAPS
- List changed files (git does this)
- Include detailed statistics (lines changed, etc.)
- Add meta-commentary ("Generated with...", "Co-Authored-By...")
- Document "benefits" or justifications (focus on the technical change)
- Include irrelevant context (stars, contributors, popularity metrics)
- Enumerate what changed (the diff shows this)
- Explain file-by-file changes (git diff does this)

### Breaking Changes

For breaking changes, add `!` after type/scope and explain in footer:

```
feat(api)!: change task queue API structure

BREAKING CHANGE: TaskQueue.get_tasks() now returns QueuedTask objects
instead of plain dicts. Update all callers accordingly.
```

## Development Workflow

### Fork Setup

Tessera uses a fork-based workflow:

```bash
# One-time setup
git clone git@github.com:wgordon17/tessera.git  # Your fork
cd tessera
git remote add upstream git@github.com:tessera-agents/tessera.git

# Verify remotes
git remote -v
# origin    git@github.com:wgordon17/tessera.git
# upstream  git@github.com:tessera-agents/tessera.git
```

### Feature Development

1. **Sync with upstream:**
   ```bash
   git checkout main
   git pull upstream main
   git push origin main
   ```

2. **Create feature branch:**
   ```bash
   git checkout -b feat/my-feature
   ```

3. **Make changes with atomic commits:**
   - Follow commit message guidelines
   - One logical change per commit
   - Test each commit

4. **Push to your fork:**
   ```bash
   git push origin feat/my-feature
   ```

5. **Create PR to upstream:**
   ```bash
   gh pr create --repo tessera-agents/tessera \
     --base main \
     --head wgordon17:feat/my-feature \
     --title "feat(scope): description" \
     --body "PR description"
   ```

   Or visit: https://github.com/tessera-agents/tessera/compare

6. **After PR is merged:**
   ```bash
   git checkout main
   git pull upstream main
   git push origin main
   git branch -D feat/my-feature
   ```

### Direct Commits (Documentation Only)

For documentation-only changes (README, CONTRIBUTING, docs/):
```bash
# Make changes on main
git checkout main
git add [files]
git commit -m "docs: description"
git push origin main
git push upstream main
```

## Code Style

- Python 3.13+
- Type hints required
- Docstrings for public APIs
- pytest for testing
- ruff for formatting/linting

See `pyproject.toml` for detailed configuration.
