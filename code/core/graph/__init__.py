"""
Graph Module - Knowledge graph operations using Neo4j.

This module handles:
- Entity node creation
- Relationship edge creation
- Graph-based matching queries
"""

from .client import GraphClient
from .queries import find_matches_by_feature, find_geographic_proximity

__all__ = [
    "GraphClient",
    "find_matches_by_feature",
    "find_geographic_proximity",
]
