"""
Vector Store using PostgreSQL with pgvector.
"""

from typing import Any

import numpy as np
import psycopg2
from psycopg2.extras import execute_values


class VectorStore:
    """
    PostgreSQL + pgvector based vector store.
    
    Usage:
        store = VectorStore(connection_string)
        store.insert("doc1", "description text", embedding)
        results = store.search(query_embedding, limit=10)
    """
    
    def __init__(self, connection_string: str):
        """
        Initialize the vector store.
        
        Args:
            connection_string: PostgreSQL connection string.
        """
        self.conn = psycopg2.connect(connection_string)
        self._ensure_extension()
    
    def _ensure_extension(self) -> None:
        """Ensure pgvector extension is installed."""
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        self.conn.commit()
    
    def create_table(self, table_name: str, dimension: int) -> None:
        """
        Create a table with vector column.
        
        Args:
            table_name: Name of the table.
            dimension: Embedding dimension.
        """
        with self.conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    metadata JSONB,
                    embedding vector({dimension})
                );
                
                CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx
                ON {table_name}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
        self.conn.commit()
    
    def insert(
        self,
        table_name: str,
        doc_id: str,
        content: str,
        embedding: np.ndarray,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Insert a document with its embedding.
        
        Args:
            table_name: Target table.
            doc_id: Document identifier.
            content: Text content.
            embedding: Vector embedding.
            metadata: Optional metadata dict.
        """
        import json
        
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {table_name} (id, content, metadata, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding
                """,
                (doc_id, content, json.dumps(metadata or {}), embedding.tolist())
            )
        self.conn.commit()
    
    def search(
        self,
        table_name: str,
        query_embedding: np.ndarray,
        limit: int = 10,
        threshold: float = 0.0
    ) -> list[dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            table_name: Table to search.
            query_embedding: Query vector.
            limit: Maximum results.
            threshold: Minimum similarity score.
            
        Returns:
            List of matching documents with similarity scores.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, content, metadata,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM {table_name}
                WHERE 1 - (embedding <=> %s::vector) > %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding.tolist(), query_embedding.tolist(), 
                 threshold, query_embedding.tolist(), limit)
            )
            
            results = []
            for row in cur.fetchall():
                results.append({
                    "id": row[0],
                    "content": row[1],
                    "metadata": row[2],
                    "similarity": row[3]
                })
            
            return results
    
    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
