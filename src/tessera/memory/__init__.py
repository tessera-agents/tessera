"""
Tessera persistent memory system for agents.

Provides long-term memory that survives session loss.
"""

from .long_term import AgentMemory, ConversationHistory, MemoryStore, get_memory_store
from .vector_store import VectorMemoryStore, embed_text, semantic_search

__all__ = [
    "AgentMemory",
    "ConversationHistory",
    "MemoryStore",
    "VectorMemoryStore",
    "embed_text",
    "get_memory_store",
    "semantic_search",
]
