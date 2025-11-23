"""
Vector-based semantic memory storage.

Uses embeddings for semantic search of memories.
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config.xdg import get_tessera_cache_dir
from ..logging_config import get_logger

logger = get_logger(__name__)


class VectorMemoryStore:
    """
    Vector-based memory storage with semantic search.

    Uses simple cosine similarity on embeddings for semantic retrieval.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """
        Initialize vector memory store.

        Args:
            db_path: Database path
        """
        if db_path is None:
            cache_dir = get_tessera_cache_dir()
            db_path = cache_dir / "vector_memory.db"

        self.db_path = db_path
        self._init_db()

        logger.debug(f"VectorMemoryStore: {self.db_path}")

    def _init_db(self) -> None:
        """Initialize vector memory database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS vector_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT UNIQUE NOT NULL,
                agent_name TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                memory_type TEXT,
                created_at TEXT NOT NULL,
                metadata TEXT
            )
        """
        )

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vector_agent ON vector_memories(agent_name)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_vector_hash ON vector_memories(content_hash)"
        )

        conn.commit()
        conn.close()

    def store(
        self,
        agent_name: str,
        content: str,
        embedding: list[float],
        memory_type: str = "general",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Store memory with embedding.

        Args:
            agent_name: Agent name
            content: Memory content
            embedding: Embedding vector
            memory_type: Memory type
            metadata: Additional metadata
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO vector_memories
                (content_hash, agent_name, content, embedding_json, memory_type, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    content_hash,
                    agent_name,
                    content,
                    json.dumps(embedding),
                    memory_type,
                    datetime.now().isoformat(),
                    json.dumps(metadata) if metadata else None,
                ),
            )

            conn.commit()

        except Exception as e:
            logger.error(f"Failed to store vector memory: {e}")

        finally:
            conn.close()

    def search(
        self,
        agent_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search using embeddings.

        Args:
            agent_name: Agent name
            query_embedding: Query embedding vector
            top_k: Number of results
            memory_type: Optional type filter

        Returns:
            List of matching memories with similarity scores
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT content, embedding_json, created_at, metadata FROM vector_memories WHERE agent_name = ?"
        params = [agent_name]

        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()

        # Calculate similarities
        results = []
        for row in rows:
            stored_embedding = json.loads(row[1])
            similarity = self._cosine_similarity(query_embedding, stored_embedding)

            results.append(
                {
                    "content": row[0],
                    "similarity": similarity,
                    "created_at": row[2],
                    "metadata": json.loads(row[3]) if row[3] else None,
                }
            )

        # Sort by similarity (highest first) and return top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:top_k]

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0.0-1.0)
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)


def embed_text(text: str, model: str = "text-embedding-ada-002") -> list[float]:
    """
    Generate embedding for text.

    Args:
        text: Text to embed
        model: Embedding model

    Returns:
        Embedding vector
    """
    # Placeholder - in production would call OpenAI/etc
    # For now, return simple hash-based fake embedding
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    # Convert hash to list of floats (not real embedding, just placeholder)
    fake_embedding = [float(int(text_hash[i : i + 2], 16)) / 255.0 for i in range(0, 32, 2)]

    logger.debug(f"Generated embedding for text (length: {len(text)})")

    return fake_embedding


def semantic_search(
    agent_name: str,
    query: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Perform semantic search on agent memories.

    Args:
        agent_name: Agent name
        query: Search query
        top_k: Number of results

    Returns:
        Matching memories with similarity scores
    """
    store = VectorMemoryStore()
    query_embedding = embed_text(query)

    return store.search(agent_name, query_embedding, top_k)
