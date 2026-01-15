"""
Semantic Search - High-level search interface.
"""

from typing import Any

from .embeddings import EmbeddingModel
from .vector_store import VectorStore


class SemanticSearch:
    """
    High-level semantic search interface.
    
    Combines embedding generation with vector store search.
    
    Usage:
        search = SemanticSearch(connection_string)
        results = search.find_similar("blue hooded sweatshirt")
    """
    
    def __init__(
        self,
        connection_string: str,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize semantic search.
        
        Args:
            connection_string: PostgreSQL connection string.
            model_name: Embedding model name.
        """
        self.embedder = EmbeddingModel(model_name)
        self.store = VectorStore(connection_string)
    
    def index_document(
        self,
        table_name: str,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Index a document for semantic search.
        
        Args:
            table_name: Target table.
            doc_id: Document identifier.
            content: Text content to embed and store.
            metadata: Optional metadata.
        """
        embedding = self.embedder.embed(content)
        self.store.insert(table_name, doc_id, content, embedding, metadata)
    
    def find_similar(
        self,
        table_name: str,
        query: str,
        limit: int = 10,
        threshold: float = 0.5
    ) -> list[dict[str, Any]]:
        """
        Find documents semantically similar to query.
        
        Args:
            table_name: Table to search.
            query: Natural language query.
            limit: Maximum results.
            threshold: Minimum similarity score.
            
        Returns:
            List of matching documents with scores.
        """
        query_embedding = self.embedder.embed(query)
        return self.store.search(table_name, query_embedding, limit, threshold)
    
    def compare_texts(self, text1: str, text2: str) -> float:
        """
        Compare semantic similarity of two texts.
        
        Args:
            text1: First text (e.g., from missing person report).
            text2: Second text (e.g., from unidentified remains).
            
        Returns:
            Similarity score between 0 and 1.
        """
        return self.embedder.similarity(text1, text2)
    
    def close(self) -> None:
        """Close connections."""
        self.store.close()
