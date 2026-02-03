"""
Search Module - Vector similarity search using pgvector.

This module handles:
- Embedding generation
- Vector storage and indexing
- Semantic similarity search
"""

from .embeddings import EmbeddingModel
from .vector_store import VectorStore
from .semantic_search import SemanticSearch

__all__ = [
    "EmbeddingModel",
    "VectorStore",
    "SemanticSearch",
]
