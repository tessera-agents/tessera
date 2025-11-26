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

**Component Scopes** (for code changes):
- **agents**: Agent implementations (supervisor, interviewer, panel)
- **api**: HTTP API and sessions
- **cli**: Command-line interface
- **config**: Configuration system
- **memory**: Memory and persistence systems
- **observability**: Metrics, tracing, cost tracking
- **plugins**: Plugin system and MCP integration
- **slack**: Slack integration
- **tools**: Tool system and access control
- **workflow**: Task execution, phases, templates
- **workspace**: Workspace management and sandboxing

**Infrastructure Scopes** (for project maintenance):
- **ci**: CI/CD pipelines and workflows
- **deps**: Dependency updates
- **build**: Build system and packaging
- **repo**: Repository structure, .gitignore, etc.
- **release**: Version bumps and releases

**Documentation Scopes** (optional, can also use just `docs`):
- **troubleshooting**: Troubleshooting guide updates

**Scope Guidelines:**
- Always use a scope for component/feature changes
- Tests should use the component scope they're testing (e.g., `test(cli)`, `test(agents)`)
- Infrastructure changes use infrastructure scopes (e.g., `chore(ci)`, `chore(deps)`)
- Docs can use just `docs:` or specific scope (e.g., `docs(troubleshooting):`)
- Scope omission is acceptable ONLY for cross-cutting changes (e.g., `fix: resolve 6 failing tests`)

**Deprecated Scopes** (use alternatives):
- `supervisor`, `interviewer`, `panel` → use `agents`
- `templates` → use `workflow`
- `tests` (without scope) → use `test(component)`
- `types`, `typing` → use the component scope (e.g., `fix(cli)` not `fix(typing)`)
- `session` → use `api`
- `dev`, `lint` → use `repo` or `ci`

### Examples

**Good:**
```
feat(memory): add persistent agent memory system
test(workspace): add memory and workspace tests
fix(cli): resolve type errors in main command
chore(deps): add google-cloud-aiplatform
docs(troubleshooting): add memory/workspace help
```

**Also Good (scope optional for cross-cutting):**
```
docs: fix critical inaccuracies
style: add quotes to type expressions
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
     --body "Brief description"
   ```

   Or visit: https://github.com/tessera-agents/tessera/compare

## Pull Request Guidelines

**Keep PR descriptions brief:**
- State what changed and why
- Use bullet points for multiple changes
- Reference related issues/PRs
- No verification sections, file lists, or checklists

**DO:**
```
Fixes CI failures from #13:

1. Ruff violations in tests/
   - Expanded per-file-ignores for test files
   - Added PLR2004 (magic values), PLR0913 (many args), SIM117 (nested with)

2. Documentation build failures (mkdocs --strict)
   - Fixed 10 broken links to non-existent documentation
   - Redirected links to existing relevant pages
```

**DON'T:**
```
## Summary
This PR addresses CI failures that occurred after merging #13...
[Multiple paragraphs of context]

## Changes
### 1. Ruff Configuration
We needed to expand the per-file-ignores because...
[Detailed rationale for each change]

## Verification
- ✓ ruff check: 0 violations
- ✓ mkdocs build: passed
- ✓ tests: 392 passing
[Test results that CI already shows]

## Files Changed
- pyproject.toml
- docs/index.md
[List of every file]

## Checklist
- [x] Tests pass
- [x] Documentation builds
[Obvious requirements]
```

The bad example includes unnecessary context, detailed rationale, verification results, file listings, and checklists. Just state what changed and why.

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
