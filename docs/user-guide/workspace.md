# Workspace Management

Tessera's workspace system provides project isolation, sandboxing, and filesystem protection to safely manage multiple projects with agent-driven execution.

## Overview

Workspaces provide:

- **Project Isolation**: Each workspace is a separate directory with its own context
- **Workspace Registry**: Global tracking of all workspaces across your system
- **Archive Support**: Save and restore workspace snapshots
- **Sandboxing**: Resource limits and process isolation for safe agent execution
- **Filesystem Protection**: Permission system to prevent unauthorized file access

## Workspace Manager

The workspace manager tracks all projects globally and provides directory switching, archival, and workspace-specific configuration.

### Registering a Workspace

```python
from tessera.workspace import get_workspace_manager

manager = get_workspace_manager()

# Register a new workspace
workspace = manager.register_workspace(
    name="my_api_project",
    path=Path("/home/user/projects/my-api"),
    metadata={"framework": "FastAPI", "language": "Python"}
)

print(f"Registered: {workspace.name} at {workspace.path}")
```

### Listing Workspaces

```python
# List all active workspaces
workspaces = manager.list_workspaces()

for ws in workspaces:
    print(f"{ws.name}: {ws.path}")
    print(f"  Last accessed: {ws.last_accessed}")
    print(f"  Archived: {ws.archived}")

# Include archived workspaces
all_workspaces = manager.list_workspaces(include_archived=True)
```

### Switching Workspaces

```python
# Enter a workspace (changes working directory)
success = manager.enter_workspace("my_api_project")

if success:
    print(f"Now in workspace: {Path.cwd()}")
```

### Getting Current Workspace

```python
# Get workspace for current directory
current = manager.get_current_workspace()

if current:
    print(f"Working in: {current.name}")
else:
    print("Not in a tracked workspace")
```

### Archiving Workspaces

```python
# Archive a workspace (creates .tar.gz)
manager.archive_workspace("old_project")
# Creates: ~/.cache/tessera/workspace_archives/old_project_YYYYMMDD_HHMMSS.tar.gz

# Unarchive a workspace
manager.unarchive_workspace("old_project")

# Unarchive to different location
manager.unarchive_workspace(
    "old_project",
    extract_path=Path("/home/user/restored/old_project")
)
```

### Deleting Workspaces

```python
# Remove from registry only (keep files)
manager.delete_workspace("temp_project")

# Delete workspace AND all files
manager.delete_workspace("temp_project", delete_files=True)
```

## Sandboxing

Sandboxes provide resource limits and filesystem protection for safe agent execution.

**Note:** Sandboxing requires UNIX-like systems (uses the `resource` module). Network blocking uses proxy environment variables, not true network isolation. The workspace uses `chdir()` for directory isolation, not chroot-level isolation.

### Creating a Sandbox

```python
from tessera.workspace import create_sandbox
from pathlib import Path

# Default sandbox (permissive)
sandbox = create_sandbox(
    workspace_root=Path("/home/user/project"),
    strict=False
)

# Strict sandbox (restricted)
strict_sandbox = create_sandbox(
    workspace_root=Path("/home/user/project"),
    strict=True
)
```

### Sandbox Configuration

```python
from tessera.workspace import Sandbox, SandboxConfig

config = SandboxConfig(
    workspace_root=Path("/home/user/project"),
    max_memory_mb=2048,           # 2GB memory limit
    max_cpu_time_seconds=600,      # 10 minutes CPU time
    max_file_size_mb=100,          # 100MB per file
    max_open_files=1024,           # File descriptor limit
    max_processes=50,              # Process limit
    network_access=True,           # Allow network
    allow_shell=False              # Disable shell execution
)

sandbox = Sandbox(config)
```

### Using a Sandbox

```python
# Context manager (recommended)
with sandbox:
    # Resource limits are active here
    result = sandbox.execute_sandboxed(
        command=["python", "script.py"],
        timeout=300
    )
    print(result.stdout)
# Limits removed on exit

# Manual control
sandbox.enter()
# ... do work ...
sandbox.exit()
```

### Executing Commands in Sandbox

```python
# Execute with sandbox limits
result = sandbox.execute_sandboxed(
    command=["pytest", "tests/"],
    cwd=Path("/home/user/project"),
    env={"PYTEST_WORKERS": "4"},
    timeout=600
)

print(f"Exit code: {result.returncode}")
print(f"Output: {result.stdout}")

if result.returncode != 0:
    print(f"Errors: {result.stderr}")
```

### Sandbox Presets

**Default Sandbox** (permissive):
- 4GB memory
- 30 minutes CPU time
- 500MB max file size
- 2048 open files
- 100 processes
- Network enabled
- Shell enabled

**Strict Sandbox** (restricted):
- 1GB memory
- 5 minutes CPU time
- 50MB max file size
- 512 open files
- 25 processes
- Network disabled
- Shell disabled

## Filesystem Protection

The filesystem guard prevents agents from accessing files outside allowed paths.

### Creating a Filesystem Guard

```python
from tessera.workspace import FilesystemGuard, PathPermission
from pathlib import Path

guard = FilesystemGuard(
    workspace_root=Path("/home/user/project"),
    allowed_paths=[
        Path("/home/user/shared"),
        Path("/tmp/tessera")
    ],
    blocked_paths=[
        Path("/home/user/project/secrets")
    ]
)
```

### Checking Path Access

```python
# Check if read is allowed
allowed, reason = guard.is_path_allowed(
    Path("/home/user/project/src/main.py"),
    permission=PathPermission.READ
)

if allowed:
    # Safe to read
    content = Path("/home/user/project/src/main.py").read_text()
else:
    print(f"Access denied: {reason}")
```

### Permission Types

```python
from tessera.workspace import PathPermission

# Available permissions:
PathPermission.READ      # Read file contents
PathPermission.WRITE     # Modify file contents
PathPermission.EXECUTE   # Execute file
PathPermission.DELETE    # Delete file
```

### Checking Operations

```python
# Verify write operation
allowed, reason = guard.check_operation(
    Path("/home/user/project/output.txt"),
    PathPermission.WRITE
)

if not allowed:
    print(f"Cannot write: {reason}")
    # Possible reasons:
    # - "outside_workspace": Path not in allowed paths
    # - "blocked_path": Path explicitly blocked
    # - "critical_file": Protected system file
    # - "invalid_path": Path doesn't exist or malformed
```

### Protected Files

The filesystem guard automatically blocks access to sensitive files:

- `.git` directories
- `.env` files
- `credentials.json`, `secrets.yaml`
- `~/.ssh/`
- `~/.aws/`
- `~/.config/gcloud/`
- `/etc/`, `/var/`, `/sys/`

### Managing Allowed Paths

```python
# Add allowed path
guard.add_allowed_path(Path("/home/user/external-lib"))

# List allowed directories
allowed = guard.list_allowed_directories()
for path in allowed:
    print(f"Allowed: {path}")

# Remove allowed path (except workspace root)
guard.remove_allowed_path(Path("/home/user/external-lib"))

# Block a path
guard.block_path(Path("/home/user/project/confidential"))
```

### Safe Path Resolution

```python
# Get safely resolved path
safe_path = guard.get_safe_path("../../../etc/passwd")

if safe_path:
    # Path is allowed
    print(f"Safe path: {safe_path}")
else:
    # Path blocked or invalid
    print("Access denied")
```

### Standalone Path Checking

```python
from tessera.workspace import check_path_access, PathPermission

# Quick permission check
allowed, reason = check_path_access(
    Path("/home/user/project/data.json"),
    permission=PathPermission.WRITE
)
```

## Integration with Agents

Workspaces integrate seamlessly with agent execution:

```python
from tessera.workspace import get_workspace_manager, create_sandbox

# Setup workspace for agent task
manager = get_workspace_manager()
workspace = manager.register_workspace(
    name="agent_task_123",
    path=Path("/tmp/agent_workspace"),
    metadata={"task_id": "123", "agent": "code_generator"}
)

# Create sandbox for the workspace
sandbox = create_sandbox(
    workspace_root=workspace.path,
    strict=True  # Use strict mode for untrusted code
)

# Execute agent work in sandbox
with sandbox:
    manager.enter_workspace("agent_task_123")

    # Agent performs work here with:
    # - Resource limits
    # - Filesystem protection
    # - Process isolation

    # Archive completed work
    manager.archive_workspace("agent_task_123")
```

## Configuration

Workspace data is stored in XDG directories:

- **Registry**: `~/.config/tessera/workspaces.json`
- **Archives**: `~/.cache/tessera/workspace_archives/`

The workspace manager handles storage automatically - no manual configuration needed.

## CLI Commands

While workspace management is primarily programmatic, you can interact via Python:

```python
# List all workspaces
from tessera.workspace import get_workspace_manager

manager = get_workspace_manager()
for ws in manager.list_workspaces():
    status = "📦 Archived" if ws.archived else "✓ Active"
    print(f"{status} {ws.name}: {ws.path}")
```

## Best Practices

### Workspace Organization

- **One workspace per project**: Keep projects isolated
- **Descriptive names**: Use meaningful workspace names
- **Metadata**: Add project context for easy filtering
- **Regular cleanup**: Archive or delete unused workspaces

### Sandbox Usage

- **Default for development**: Use permissive sandbox during development
- **Strict for production**: Use strict sandbox for untrusted code
- **Timeout commands**: Always set timeouts for long-running operations
- **Monitor resources**: Check sandbox stats to tune limits

```python
stats = sandbox.get_stats()
print(f"Memory limit: {stats['max_memory_mb']}MB")
print(f"Network access: {stats['network_access']}")
```

### Filesystem Security

- **Minimal permissions**: Only allow what's needed
- **Block sensitive paths**: Explicitly block confidential directories
- **Validate paths**: Always check permissions before file operations
- **Audit access**: Log denied operations for security review

### Error Handling

```python
try:
    with sandbox:
        result = sandbox.execute_sandboxed(["python", "script.py"])
except subprocess.TimeoutExpired:
    print("Command timed out - increase timeout or optimize script")
except PermissionError:
    print("Insufficient permissions - check filesystem guard")
except Exception as e:
    print(f"Execution failed: {e}")
```

## Troubleshooting

### Workspace Not Found

```python
workspace = manager.get_workspace("missing_project")
if workspace is None:
    print("Workspace not registered")
    # Register it:
    manager.register_workspace("missing_project", Path("/path/to/project"))
```

### Archive Extraction Fails

```python
# Check if archive exists
workspace = manager.get_workspace("archived_project")
if workspace and workspace.archive_path:
    if workspace.archive_path.exists():
        manager.unarchive_workspace("archived_project")
    else:
        print(f"Archive not found: {workspace.archive_path}")
```

### Sandbox Resource Limits

If processes are being killed by resource limits:

```python
# Increase limits
config = SandboxConfig(
    workspace_root=Path("/project"),
    max_memory_mb=8192,      # Increase to 8GB
    max_cpu_time_seconds=1800  # Increase to 30 minutes
)
sandbox = Sandbox(config)
```

### Permission Denied Errors

```python
from tessera.workspace import FilesystemGuard, PathPermission

guard = FilesystemGuard(workspace_root=Path.cwd())

# Debug permission issue
path = Path("/path/to/file")
allowed, reason = guard.is_path_allowed(path, PathPermission.WRITE)

print(f"Path: {path}")
print(f"Allowed: {allowed}")
print(f"Reason: {reason}")

if not allowed:
    # Add to allowed paths if safe
    guard.add_allowed_path(path.parent)
```

## Advanced Usage

### Custom Sandbox Configurations

```python
# Create specialized sandbox for specific task
web_scraper_sandbox = Sandbox(SandboxConfig(
    workspace_root=Path("/tmp/scraper"),
    max_memory_mb=512,         # Low memory
    max_cpu_time_seconds=120,   # Short timeout
    network_access=True,        # Need network
    allow_shell=False           # No shell access
))

# Data processing sandbox
data_processor_sandbox = Sandbox(SandboxConfig(
    workspace_root=Path("/data/processing"),
    max_memory_mb=16384,        # 16GB for large datasets
    max_cpu_time_seconds=3600,  # 1 hour processing
    max_file_size_mb=1024,      # 1GB files allowed
    network_access=False        # No network needed
))
```

### Workspace Metadata

Use metadata for workspace management:

```python
# Register with rich metadata
workspace = manager.register_workspace(
    name="ml_training",
    path=Path("/ml/projects/training"),
    metadata={
        "project_type": "machine_learning",
        "framework": "PyTorch",
        "gpu_required": True,
        "python_version": "3.11",
        "last_model": "model_v2.pth",
        "dataset": "imagenet_subset"
    }
)

# Query by metadata
ml_workspaces = [
    ws for ws in manager.list_workspaces()
    if ws.metadata and ws.metadata.get("project_type") == "machine_learning"
]
```

## Future Enhancements

Planned improvements:

- **Docker integration**: Full container-based sandboxing
- **Network isolation**: Fine-grained network access control
- **Workspace templates**: Quick setup for common project types
- **Resource monitoring**: Real-time tracking of sandbox resource usage
- **Cloud workspaces**: Support for remote workspace storage
- **Multi-user support**: Shared workspaces with permissions
