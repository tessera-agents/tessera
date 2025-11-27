"""
Long-term memory storage for agents.

Persists agent conversations, decisions, and learnings across sessions.
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config.xdg import get_tessera_cache_dir
from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ConversationHistory:
    """Single conversation entry."""

    timestamp: datetime
    agent_name: str
    role: str  # "user", "assistant", "system"
    content: str
    task_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class AgentMemory:
    """Agent memory entry."""

    agent_name: str
    memory_type: str  # "fact", "decision", "learning", "error"
    content: str
    confidence: float
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    metadata: dict[str, Any] | None = None


class MemoryStore:
    """
    Persistent memory storage for agents.

    Stores:
    - Conversation histories
    - Agent learnings and decisions
    - Facts and knowledge
    - Error patterns

    Survives session restarts.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """
        Initialize memory store.

        Args:
            db_path: Database path (defaults to XDG cache)
        """
        if db_path is None:
            cache_dir = get_tessera_cache_dir()
            db_path = cache_dir / "agent_memory.db"

        self.db_path = db_path
        self._init_db()

        logger.debug(f"MemoryStore: {self.db_path}")

    def _init_db(self) -> None:
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Conversation history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                task_id TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Agent memory table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                metadata TEXT,
                UNIQUE(agent_name, memory_type, content)
            )
        """
        )

        # Indexes for fast queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversation_agent ON conversation_history(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversation_task ON conversation_history(task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_agent ON agent_memory(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON agent_memory(memory_type)")

        conn.commit()
        conn.close()

    def add_conversation(
        self,
        agent_name: str,
        role: str,
        content: str,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add conversation entry.

        Args:
            agent_name: Agent name
            role: Message role (user/assistant/system)
            content: Message content
            task_id: Related task ID
            metadata: Additional metadata
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO conversation_history
            (timestamp, agent_name, role, content, task_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                datetime.now(UTC).isoformat(),
                agent_name,
                role,
                content,
                task_id,
                json.dumps(metadata) if metadata else None,
            ),
        )

        conn.commit()
        conn.close()

        logger.debug(f"Added conversation entry for {agent_name}")

    def get_conversation_history(
        self,
        agent_name: str | None = None,
        task_id: str | None = None,
        limit: int = 100,
    ) -> list[ConversationHistory]:
        """
        Get conversation history.

        Args:
            agent_name: Optional agent filter
            task_id: Optional task filter
            limit: Max entries to return

        Returns:
            List of conversation entries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT timestamp, agent_name, role, content, task_id, metadata FROM conversation_history WHERE 1=1"
        params = []

        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)

        if task_id:
            query += " AND task_id = ?"
            params.append(task_id)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()

        return [
            ConversationHistory(
                timestamp=datetime.fromisoformat(row[0]),
                agent_name=row[1],
                role=row[2],
                content=row[3],
                task_id=row[4],
                metadata=json.loads(row[5]) if row[5] else None,
            )
            for row in rows
        ]

    def add_memory(
        self,
        agent_name: str,
        memory_type: str,
        content: str,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add agent memory.

        Args:
            agent_name: Agent name
            memory_type: Memory type (fact/decision/learning/error)
            content: Memory content
            confidence: Confidence score (0.0-1.0)
            metadata: Additional metadata
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now(UTC).isoformat()

        try:
            cursor.execute(
                """
                INSERT INTO agent_memory
                (agent_name, memory_type, content, confidence, created_at, last_accessed, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_name, memory_type, content)
                DO UPDATE SET
                    confidence = excluded.confidence,
                    last_accessed = excluded.last_accessed,
                    access_count = access_count + 1
            """,
                (
                    agent_name,
                    memory_type,
                    content,
                    confidence,
                    now,
                    now,
                    json.dumps(metadata) if metadata else None,
                ),
            )

            conn.commit()

        except OSError as e:
            logger.exception(f"Failed to add memory: {e}")

        finally:
            conn.close()

    def get_memories(
        self,
        agent_name: str,
        memory_type: str | None = None,
        min_confidence: float = 0.0,
        limit: int = 100,
    ) -> list[AgentMemory]:
        """
        Get agent memories.

        Args:
            agent_name: Agent name
            memory_type: Optional type filter
            min_confidence: Minimum confidence threshold
            limit: Max entries

        Returns:
            List of memories
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT agent_name, memory_type, content, confidence,
                   created_at, last_accessed, access_count, metadata
            FROM agent_memory
            WHERE agent_name = ? AND confidence >= ?
        """
        params = [agent_name, min_confidence]

        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)

        query += " ORDER BY last_accessed DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()

        return [
            AgentMemory(
                agent_name=row[0],
                memory_type=row[1],
                content=row[2],
                confidence=row[3],
                created_at=datetime.fromisoformat(row[4]),
                last_accessed=datetime.fromisoformat(row[5]),
                access_count=row[6],
                metadata=json.loads(row[7]) if row[7] else None,
            )
            for row in rows
        ]

    def search_memories(
        self,
        agent_name: str,
        search_term: str,
        memory_type: str | None = None,
    ) -> list[AgentMemory]:
        """
        Search memories by content.

        Args:
            agent_name: Agent name
            search_term: Search term
            memory_type: Optional type filter

        Returns:
            Matching memories
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT agent_name, memory_type, content, confidence,
                   created_at, last_accessed, access_count, metadata
            FROM agent_memory
            WHERE agent_name = ? AND content LIKE ?
        """
        params = [agent_name, f"%{search_term}%"]

        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()

        return [
            AgentMemory(
                agent_name=row[0],
                memory_type=row[1],
                content=row[2],
                confidence=row[3],
                created_at=datetime.fromisoformat(row[4]),
                last_accessed=datetime.fromisoformat(row[5]),
                access_count=row[6],
                metadata=json.loads(row[7]) if row[7] else None,
            )
            for row in rows
        ]

    def clear_agent_memory(self, agent_name: str) -> int:
        """
        Clear all memory for an agent.

        Args:
            agent_name: Agent name

        Returns:
            Number of entries deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM agent_memory WHERE agent_name = ?", (agent_name,))
        deleted = cursor.rowcount

        cursor.execute("DELETE FROM conversation_history WHERE agent_name = ?", (agent_name,))
        deleted += cursor.rowcount

        conn.commit()
        conn.close()

        logger.info(f"Cleared {deleted} memory entries for {agent_name}")

        return deleted


# Global memory store
_memory_store: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    """
    Get global memory store instance.

    Returns:
        Global MemoryStore
    """
    global _memory_store

    if _memory_store is None:
        _memory_store = MemoryStore()

    return _memory_store
