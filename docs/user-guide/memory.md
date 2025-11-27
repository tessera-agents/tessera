# Memory System

Tessera provides a persistent memory system that allows agents to remember conversations, learnings, and decisions across sessions. This enables agents to build context over time and improve their performance through accumulated knowledge.

## Overview

The memory system consists of two components:

1. **Long-Term Memory**: Stores conversation histories, facts, decisions, and learnings in a SQLite database
2. **Vector Memory**: Provides semantic search capabilities using embeddings for intelligent memory retrieval

Memory is stored in your XDG cache directory (typically `~/.cache/tessera/`) and persists across all Tessera sessions.

## Features

### Conversation History

Track all agent interactions with full context:

- Agent name and role (user/assistant/system)
- Message content and timestamps
- Associated task IDs
- Custom metadata

### Agent Memory Types

Agents can store different types of memories:

- **Facts**: Verified information and knowledge
- **Decisions**: Important choices made during execution
- **Learnings**: Insights gained from experience
- **Errors**: Failure patterns and debugging insights

Each memory includes:

- Confidence score (0.0-1.0)
- Creation and access timestamps
- Access count for importance tracking
- Optional metadata

### Semantic Search

Vector-based memory uses embeddings to find relevant memories based on semantic similarity, not just keyword matching.

## Usage

### Basic Memory Operations

```python
from tessera.memory import get_memory_store

# Get the global memory store
memory = get_memory_store()

# Add a conversation entry
memory.add_conversation(
    agent_name="code_reviewer",
    role="assistant",
    content="Review completed. Found 3 security issues.",
    task_id="task_123",
    metadata={"severity": "high"}
)

# Add an agent memory
memory.add_memory(
    agent_name="code_reviewer",
    memory_type="learning",
    content="SQL injection patterns often appear in user input handling",
    confidence=0.95,
    metadata={"category": "security"}
)
```

### Retrieving Memories

```python
# Get conversation history
conversations = memory.get_conversation_history(
    agent_name="code_reviewer",
    limit=50
)

for conv in conversations:
    print(f"{conv.timestamp} - {conv.role}: {conv.content}")

# Get agent memories
memories = memory.get_memories(
    agent_name="code_reviewer",
    memory_type="learning",
    min_confidence=0.8
)

# Search memories
results = memory.search_memories(
    agent_name="code_reviewer",
    search_term="security"
)
```

### Vector-Based Semantic Search

**WARNING: Development Implementation**

The `embed_text()` function is currently a **placeholder implementation** that uses hash-based fake embeddings for development and testing purposes. It does NOT provide real semantic embeddings.

For production use, you must implement real embeddings using:
- OpenAI's text-embedding-ada-002 or text-embedding-3-small
- Google's Vertex AI embeddings
- Other embedding providers

```python
from tessera.memory import VectorMemoryStore, embed_text

vector_store = VectorMemoryStore()

# Store memory with embedding
content = "Always validate user input before database queries"

# NOTE: embed_text() currently uses hash-based fake embeddings
# Production use requires implementing real embeddings
embedding = embed_text(content)

vector_store.store(
    agent_name="code_reviewer",
    content=content,
    embedding=embedding,
    memory_type="best_practice"
)

# Semantic search
query = "how to prevent SQL injection"
query_embedding = embed_text(query)

results = vector_store.search(
    agent_name="code_reviewer",
    query_embedding=query_embedding,
    top_k=5
)

for result in results:
    print(f"Similarity: {result['similarity']:.2f}")
    print(f"Content: {result['content']}")
```

### Memory Management

```python
# Clear all memory for an agent
deleted_count = memory.clear_agent_memory("code_reviewer")
print(f"Deleted {deleted_count} memory entries")

# Filter by task
task_conversations = memory.get_conversation_history(
    task_id="task_123"
)
```

## Memory Lifecycle

1. **Creation**: Memories are created during agent execution
2. **Storage**: Persisted to SQLite database in cache directory
3. **Retrieval**: Accessed via queries or semantic search
4. **Updates**: Duplicate memories update confidence and access count
5. **Cleanup**: Manual cleanup via `clear_agent_memory()`

## Configuration

Memory system uses XDG Base Directory specification:

- **Database Location**: `~/.cache/tessera/agent_memory.db`
- **Vector Database**: `~/.cache/tessera/vector_memory.db`

No configuration required - the system initializes automatically on first use.

## Memory Types and Use Cases

### Facts
Store verified information that agents learn:

```python
memory.add_memory(
    agent_name="researcher",
    memory_type="fact",
    content="Project uses FastAPI 0.104.1",
    confidence=1.0
)
```

### Decisions
Record important choices for future reference:

```python
memory.add_memory(
    agent_name="architect",
    memory_type="decision",
    content="Chose PostgreSQL over MySQL for better JSON support",
    confidence=0.9,
    metadata={"alternatives": ["MySQL", "SQLite"]}
)
```

### Learnings
Capture insights from experience:

```python
memory.add_memory(
    agent_name="tester",
    memory_type="learning",
    content="Integration tests catch more bugs than unit tests in this codebase",
    confidence=0.85
)
```

### Errors
Track failure patterns:

```python
memory.add_memory(
    agent_name="executor",
    memory_type="error",
    content="Docker build fails when .dockerignore is missing",
    confidence=1.0,
    metadata={"error_code": "BUILD_FAILED", "solution": "Add .dockerignore"}
)
```

## Best Practices

### Confidence Scores

- **1.0**: Verified facts and confirmed decisions
- **0.8-0.9**: High confidence learnings from multiple observations
- **0.6-0.7**: Tentative learnings requiring more validation
- **Below 0.6**: Experimental insights, use with caution

### Metadata Usage

Add context to make memories more useful:

```python
memory.add_memory(
    agent_name="security_auditor",
    memory_type="learning",
    content="This project uses JWT for authentication",
    confidence=1.0,
    metadata={
        "file": "src/auth.py",
        "line_number": 45,
        "category": "authentication",
        "framework": "FastAPI"
    }
)
```

### Memory Cleanup

Regularly clean up outdated memories:

```python
# Clear low-confidence memories
memories = memory.get_memories(agent_name="researcher")
for mem in memories:
    if mem.confidence < 0.5 and mem.access_count == 0:
        # Delete if never accessed and low confidence
        memory.clear_agent_memory(mem.agent_name)
```

## Performance Considerations

- **Indexing**: Memory tables are indexed on agent_name, task_id, and memory_type
- **Limits**: Use `limit` parameter to control result set size
- **Caching**: The global memory store is a singleton for efficiency
- **Embeddings**: Vector search requires embedding generation (future: external API support)

## Troubleshooting

### Database Location

Find your memory database:

```python
from tessera.config.xdg import get_tessera_cache_dir

cache_dir = get_tessera_cache_dir()
print(f"Memory database: {cache_dir / 'agent_memory.db'}")
```

### Database Size

Monitor database growth:

```bash
ls -lh ~/.cache/tessera/agent_memory.db
```

### Corrupted Database

If the database becomes corrupted:

```bash
# Backup first
cp ~/.cache/tessera/agent_memory.db ~/.cache/tessera/agent_memory.db.backup

# Remove and let Tessera recreate
rm ~/.cache/tessera/agent_memory.db
```

The system will automatically recreate the database on next use.

## Future Enhancements

Planned improvements for the memory system:

- **Automatic summarization**: Compress old memories
- **Memory importance scoring**: Rank memories by usefulness
- **Cross-agent memory sharing**: Enable knowledge transfer
- **External embedding APIs**: Integration with OpenAI/Vertex AI for production embeddings
- **Memory expiration**: Automatic cleanup of stale memories
