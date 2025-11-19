# Tools & Plugins

Tessera provides built-in tools and supports custom extensions via Python plugins and MCP servers.

---

## Built-in Tools

### File Operations
- `read_file` - Read file contents
- `write_file` - Write to files
- `delete_file` - Delete files
- `list_directory` - List directory contents

### Git Operations
- `git_status` - Check repository status
- `git_commit` - Create commits
- `git_push` - Push to remote
- `create_pr` - Create pull requests

### Web Operations
- `web_search` - Search the web
- `fetch_url` - Retrieve web pages
- `scrape_page` - Extract content

### Code Execution
- `execute_python` - Run Python code
- `execute_shell` - Run shell commands
- `run_tests` - Execute test suite

---

## Tool Access Control

Configure which tools agents can use:

```yaml
tools:
  global:
    strategy: "risk-based"
    max_risk_level: "high"

  builtin:
    filesystem:
      enabled: true
      approval_required: ["write_file", "delete_file"]

    execution:
      enabled: true
      approval_required: true  # All execution needs approval
```

---

## Python Plugins

Add custom tools via Python files:

### Plugin Location

```
~/.config/tessera/plugins/my_tool.py
```

### Plugin Example

```python
from tessera.plugins import tool

@tool(
    name="send_email",
    description="Send email via Gmail API",
    risk_level="medium",
    approval_required=True
)
def send_gmail(to: str, subject: str, body: str) -> str:
    # Implementation
    return "Email sent"
```

### Plugin Configuration

```yaml
tools:
  plugins:
    discovery:
      - "~/.config/tessera/plugins/*.py"

    definitions:
      - name: "gmail-tool"
        file: "~/.config/tessera/plugins/gmail.py"
        enabled: true
        risk_level: "medium"
```

---

## MCP Integration

Connect to Model Context Protocol servers:

```yaml
tools:
  mcp:
    - name: "filesystem-mcp"
      enabled: true
      type: "stdio"
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem"]
      env:
        ALLOWED_DIRECTORIES: "./,~/.config/tessera"
```

---

## Risk Levels

Tools are classified by risk:

- **safe** - Read-only operations
- **low** - Local modifications in safe paths
- **medium** - File writes, installations
- **high** - Deletions, system commands
- **critical** - Git push, deployments

---

## Tool Development

See [Custom Plugins](../advanced/custom-plugins.md) for detailed plugin development guide.

---

## Next Steps

- [Configuration](configuration.md)
- [Agents](agents.md)
- [CLI Reference](../reference/cli.md)
