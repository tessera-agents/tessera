"""Tests for agent memory system."""

import tempfile
from pathlib import Path

import pytest

from tessera.memory.long_term import MemoryStore
from tessera.memory.vector_store import VectorMemoryStore, embed_text


@pytest.mark.unit
class TestMemoryStore:
    """Test long-term memory storage."""

    def test_memory_store_initialization(self):
        """Test memory store initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.db"
            store = MemoryStore(db_path)

            assert store.db_path == db_path
            assert db_path.exists()

    def test_add_conversation(self):
        """Test adding conversation entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")

            store.add_conversation(
                agent_name="test-agent",
                role="assistant",
                content="This is a test message",
                task_id="task-123",
            )

            # Verify via get
            history = store.get_conversation_history(agent_name="test-agent")

            assert len(history) == 1
            assert history[0].agent_name == "test-agent"
            assert history[0].role == "assistant"
            assert history[0].content == "This is a test message"

    def test_get_conversation_history_filtered(self):
        """Test getting conversation history with filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")

            store.add_conversation("agent1", "user", "Message 1", "task1")
            store.add_conversation("agent1", "assistant", "Response 1", "task1")
            store.add_conversation("agent2", "user", "Message 2", "task2")

            # Filter by agent
            agent1_history = store.get_conversation_history(agent_name="agent1")
            assert len(agent1_history) == 2

            # Filter by task
            task1_history = store.get_conversation_history(task_id="task1")
            assert len(task1_history) == 2

    def test_add_memory(self):
        """Test adding agent memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")

            store.add_memory(
                agent_name="python-expert",
                memory_type="fact",
                content="Python uses duck typing",
                confidence=0.95,
            )

            memories = store.get_memories("python-expert")

            assert len(memories) == 1
            assert memories[0].memory_type == "fact"
            assert memories[0].confidence == 0.95

    def test_get_memories_filtered(self):
        """Test getting memories with filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")

            store.add_memory("agent1", "fact", "Fact 1", 0.9)
            store.add_memory("agent1", "decision", "Decision 1", 0.8)
            store.add_memory("agent1", "fact", "Fact 2", 0.7)

            # Filter by type
            facts = store.get_memories("agent1", memory_type="fact")
            assert len(facts) == 2

            # Filter by confidence
            high_conf = store.get_memories("agent1", min_confidence=0.85)
            assert len(high_conf) == 2

    def test_search_memories(self):
        """Test searching memories by content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")

            store.add_memory("agent1", "fact", "Python is dynamically typed", 1.0)
            store.add_memory("agent1", "fact", "JavaScript has prototypes", 1.0)

            results = store.search_memories("agent1", "Python")

            assert len(results) == 1
            assert "Python" in results[0].content

    def test_clear_agent_memory(self):
        """Test clearing all memory for an agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(Path(tmpdir) / "memory.db")

            store.add_conversation("agent1", "user", "Message", "task1")
            store.add_memory("agent1", "fact", "Fact", 1.0)

            deleted = store.clear_agent_memory("agent1")

            assert deleted == 2

            # Verify cleared
            history = store.get_conversation_history(agent_name="agent1")
            memories = store.get_memories("agent1")

            assert len(history) == 0
            assert len(memories) == 0


@pytest.mark.unit
class TestVectorMemoryStore:
    """Test vector-based memory storage."""

    def test_vector_store_initialization(self):
        """Test vector store initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "vectors.db"
            store = VectorMemoryStore(db_path)

            assert store.db_path == db_path
            assert db_path.exists()

    def test_store_memory_with_embedding(self):
        """Test storing memory with embedding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorMemoryStore(Path(tmpdir) / "vectors.db")

            embedding = [0.1, 0.2, 0.3, 0.4]

            store.store(
                agent_name="test-agent",
                content="Test memory content",
                embedding=embedding,
                memory_type="fact",
            )

            # Search should find it
            query_embedding = [0.1, 0.2, 0.3, 0.4]  # Identical
            results = store.search("test-agent", query_embedding, top_k=5)

            assert len(results) > 0
            assert results[0]["content"] == "Test memory content"

    def test_semantic_search(self):
        """Test semantic search by similarity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorMemoryStore(Path(tmpdir) / "vectors.db")

            # Store multiple memories
            store.store("agent1", "Python is a programming language", [1.0, 0.0, 0.0])
            store.store("agent1", "JavaScript is also a language", [0.9, 0.1, 0.0])
            store.store("agent1", "Cats are animals", [0.0, 0.0, 1.0])

            # Search for programming-related
            query = [1.0, 0.0, 0.0]  # Should match Python best
            results = store.search("agent1", query, top_k=2)

            assert len(results) == 2
            # First result should be most similar
            assert "Python" in results[0]["content"]

    def test_embed_text(self):
        """Test text embedding function."""
        embedding = embed_text("Test text")

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        store = VectorMemoryStore()

        # Identical vectors = 1.0
        sim = store._cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        assert abs(sim - 1.0) < 0.01

        # Orthogonal vectors = 0.0
        sim = store._cosine_similarity([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
        assert abs(sim - 0.0) < 0.01

        # Similar vectors = 0.5-1.0
        sim = store._cosine_similarity([1.0, 0.0, 0.0], [0.7, 0.7, 0.0])
        assert 0.4 < sim < 0.8
