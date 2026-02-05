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
from .specificity_search import SpecificityMatcher
from .narrative_generator import NarrativeGenerator

__all__ = [
    "EmbeddingModel",
    "VectorStore",
    "SemanticSearch",
    "SpecificityMatcher",
    "NarrativeGenerator",
]
