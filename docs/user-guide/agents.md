# Agents

Agents are the core workers in Tessera. Each agent is a specialized AI with specific capabilities and expertise.

---

## Defining Agents

Agents are defined in `~/.config/tessera/config.yaml`:

```yaml
agents:
  definitions:
    - name: "python-expert"
      model: "gpt-4o"
      provider: "openai"
      capabilities: ["python", "coding", "testing"]
      phase_affinity: ["implementation", "execution"]
      system_prompt_file: "~/.config/tessera/prompts/python-expert.md"
      temperature: 0.5
```

---

## Agent Properties

### Required Fields

- **name** - Unique identifier for the agent
- **model** - LLM model to use (gpt-4, claude-3-5-sonnet, etc.)
- **provider** - LLM provider (openai, vertex_ai, anthropic, etc.)

### Optional Fields

- **capabilities** - List of skills (used for task routing)
- **phase_affinity** - Which workflow phases this agent excels at
- **system_prompt_file** - Path to markdown file with agent instructions
- **system_prompt** - Inline prompt (alternative to file)
- **temperature** - LLM temperature (0.0-2.0)
- **context_size** - Max tokens
- **timeout** - Request timeout in seconds
- **max_retries** - Retry count for failed requests

---

## System Prompts

Define agent behavior with markdown prompts:

```markdown
# ~/.config/tessera/prompts/python-expert.md

You are a Python expert specializing in clean, well-tested code.

## Responsibilities
- Write Pythonic, PEP 8 compliant code
- Add comprehensive docstrings
- Include type hints
- Handle edge cases and errors

## Code Style
- Prefer list comprehensions over loops
- Use pathlib over os.path
- Add logging for debugging

## Testing
- Write pytest tests for all functions
- Aim for >90% coverage
- Test edge cases and error conditions
```

---

## Agent Capabilities

Capabilities help Tessera route tasks to the right agents:

**Common capabilities:**
- `python`, `javascript`, `rust` - Programming languages
- `testing`, `pytest`, `unittest` - Testing frameworks
- `documentation`, `writing` - Documentation
- `security`, `code-review` - Quality assurance
- `devops`, `docker`, `kubernetes` - Operations

---

## Phase Affinity

Agents can specify which workflow phases they're best suited for:

- `user_interview` - Requirements gathering
- `research` - Information collection
- `architecture` - System design
- `implementation` - Coding
- `testing` - Quality assurance
- `review` - Code review
- `documentation` - Docs writing

---

## Examples

### Specialist Agent

```yaml
- name: "security-expert"
  model: "gpt-4"
  provider: "openai"
  capabilities: ["security", "code-review", "penetration-testing"]
  phase_affinity: ["review"]
  system_prompt: |
    You are a security expert. Review code for vulnerabilities.
    Check for: SQL injection, XSS, CSRF, auth issues.
  temperature: 0.2  # Low temperature for consistency
```

### Generalist Agent

```yaml
- name: "full-stack-dev"
  model: "gpt-4o"
  provider: "openai"
  capabilities: ["python", "javascript", "sql", "docker"]
  phase_affinity: ["implementation", "testing", "documentation"]
  system_prompt_file: "~/.config/tessera/prompts/full-stack.md"
```

---

## Best Practices

1. **Specific system prompts** - Clear instructions yield better results
2. **Lower temperature for deterministic tasks** - Code review, testing
3. **Higher temperature for creative tasks** - Architecture, design
4. **Appropriate models** - Use cheaper models (gpt-4o-mini) for simple tasks
5. **Clear capabilities** - Helps supervisor route tasks correctly

---

## Next Steps

- [Configuration Guide](configuration.md)
- [Tools & Plugins](tools.md)
- [CLI Reference](../reference/cli.md)
