# Troubleshooting

Common issues and solutions for Tessera.

---

## Installation Issues

### ImportError: No module named 'tessera'

**Problem**: Tessera not installed or not in Python path

**Solution**:
```bash
#Install from PyPI
pip install tessera-agents

# Or install from source
cd tessera
uv sync
uv run tessera --version
```

### Command not found: tessera

**Problem**: CLI not in PATH

**Solution**:
```bash
# Using uvx (no install needed)
uvx tessera-agents main "your task"

# Or install as tool
uv tool install tessera-agents
tessera --version
```

---

## Configuration Issues

### No config file found

**Problem**: Config file not initialized

**Solution**:
```bash
tessera init  # Creates ~/.config/tessera/config.yaml
```

### Config validation failed

**Problem**: Invalid YAML syntax or schema

**Solution**:
```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('~/.config/tessera/config.yaml'))"

# Validate against schema
tessera init --validate
```

---

## API Key Issues

### No API key found

**Problem**: Missing LLM provider API key

**Solution**:
```bash
# Set environment variable
export OPENAI_API_KEY=sk-your-key-here

# Or use 1Password
export OP_OPENAI_ITEM=op://Private/OpenAI/credential
```

### Invalid API key format

**Problem**: Key doesn't match expected format

**Solution**:

- **OpenAI**: Must start with `sk-`
- **Anthropic**: Must start with `sk-ant-`
- **GitHub Copilot**: Must start with `ghu_` (not `ghp_`)

```bash
# Generate Copilot token
npx copilot-api@latest auth
```

---

## Execution Issues

### Proxy failed to start

**Problem**: GitHub Copilot proxy won't start

**Solution**:
```bash
# Verify Node.js installed
node --version  # Need v18+

# Install copilot-api
npm install -g copilot-api@latest

# Check token format
echo $GITHUB_TOKEN | cut -c1-4  # Should show: ghu_
```

### Tasks stuck in queue

**Problem**: Tasks not executing

**Possible Causes**:

1. **Circular dependencies**: Task A depends on B, B depends on A
2. **Missing agent**: No agent with required capabilities
3. **API rate limit**: Provider throttling requests

**Solution**:
```bash
# Check task queue status
tessera status

# Review task dependencies in logs
cat ~/.local/share/tessera/traces.jsonl | jq '.attributes.task_id'
```

### Out of memory errors

**Problem**: Large context windows exhaust RAM

**Solution**:
```yaml
# Reduce context size
agents:
  defaults:
    context_size: 4096  # Instead of 32k+

# Reduce parallel agents
workflow:
  max_parallel: 2  # Instead of 5+
```

---

## Coverage & Testing Issues

### Pytest runaway processes

**Problem**: Multiple pytest processes running

**Solution**:

This was fixed in v1.0.0. If you still see it:

```bash
# Kill all pytest
killall -9 Python

# Update to latest version
pip install --upgrade tessera-agents
```

### Coverage not reaching threshold

**Problem**: Tests fail with coverage < 85%

**Note**: This is expected during development. Coverage requirement is for Tessera's own development, not your generated projects.

---

## Cost & Token Issues

### Costs higher than expected

**Problem**: Task using more tokens/money than anticipated

**Solutions**:

1. **Set cost limits**:
```yaml
cost:
  limits:
    per_task:
      max_usd: 1.00
      enforcement: "hard"
```

2. **Use cheaper models**:
```yaml
agents:
  definitions:
    - model: gpt-4o-mini  # Cheaper than gpt-4
```

3. **Reduce context**:
```yaml
agents:
  defaults:
    context_size: 4096  # Smaller context = fewer tokens
```

### Token tracking shows 0

**Problem**: Token usage not being captured

**Possible Causes**:

- Using provider without token extraction support
- Callback not registered properly
- Streaming mode (tokens counted differently)

**Verification**:
```python
# Check if provider supports token tracking
# All major providers (OpenAI, Anthropic, Copilot) supported
```

---

## Slack Integration Issues

### Slack client creation fails

**Problem**: Missing Slack tokens

**Solution**:
```bash
export SLACK_BOT_TOKEN=xoxb-your-token
export SLACK_APP_TOKEN=xapp-your-token
export SLACK_AGENT_CHANNEL=C123456  # Channel ID
export SLACK_USER_CHANNEL=C789012
```

### Messages not appearing

**Problem**: Bot not posting to Slack

**Checks**:

1. Bot has correct scopes: `chat:write`, `chat:write.public`
2. Bot invited to channels
3. Channel IDs are correct (not channel names)

---

## Performance Issues

### Slow task execution

**Optimizations**:

```yaml
# Use faster models
agents:
  definitions:
    - model: gpt-4o  # Faster than gpt-4

# Increase parallelism
workflow:
  max_parallel: 5  # More concurrent tasks

# Reduce iteration loops
workflow:
  max_iterations: 5  # Fewer retry attempts
```

### High memory usage

**Solutions**:

- Reduce `max_parallel`
- Smaller `context_size`
- Clear SQLite database periodically

```bash
# Clear old metrics (keeps schema)
sqlite3 ~/.local/share/tessera/metrics.db "DELETE FROM agent_performance WHERE timestamp < date('now', '-30 days')"
```

---

## Getting Help

### Check Logs

```bash
# Enable debug logging
export TESSERA_LOG_LEVEL=DEBUG
tessera main "your task"

# Check traces
tail -f ~/.local/share/tessera/traces.jsonl | jq
```

### Report Issues

1. Check [GitHub Issues](https://github.com/tessera-agents/tessera/issues)
2. Include:
   - Tessera version (`tessera --version`)
   - Python version (`python --version`)
   - Error message and traceback
   - Config file (remove API keys!)
   - Steps to reproduce

---

## Common Error Messages

### "No models configured"

Add models to config:
```yaml
agents:
  definitions:
    - name: supervisor
      model: gpt-4  # ← Add this
```

### "Dry-run mode: no execution"

Remove `--dry-run` flag:
```bash
tessera main "task"  # Not: tessera main --dry-run "task"
```

### "Vertex AI authentication failed"

```bash
# Setup Vertex AI credentials
gcloud auth application-default login
export VERTEX_PROJECT=your-project-id
export VERTEX_LOCATION=us-east5
```

---

## Still Stuck?

- Read the [Configuration Guide](user-guide/configuration.md)
- Check [Multi-Agent Execution](user-guide/multi-agent.md)
- Review [Examples](https://github.com/tessera-agents/tessera/tree/main/examples)
- Ask in [GitHub Discussions](https://github.com/tessera-agents/tessera/discussions)
