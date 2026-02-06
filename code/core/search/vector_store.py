"""
Vector Store using SQLite with the sqlite-vss extension.
"""

import sqlite3
import json
from typing import Any
import numpy as np


class VectorStore:
    """
    SQLite + sqlite-vss based vector store.
    
    Usage:
        store = VectorStore(db_path)
        store.insert("doc1", "description text", embedding)
        results = store.search(query_embedding, limit=10)
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the vector store.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        # Enable extension loading
        self.conn.enable_load_extension(True)
        self._load_vss()
        self._ensure_vss_tables_exist()
    
    def _load_vss(self) -> None:
        """Load sqlite-vss extensions."""
        try:
            # Note: Extension names might vary by OS/installation
            # Common names: vss0, vector0 or ./vss0, ./vector0
            self.conn.load_extension("vector0")
            self.conn.load_extension("vss0")
        except sqlite3.OperationalError as e:
            print(f"Warning: Could not load sqlite-vss extensions: {e}")
            print("Vector search functionality will be disabled.")
    
    def _ensure_vss_tables_exist(self) -> None:
        """Ensure core tables for vector storage exist."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS vector_metadata (
                    id TEXT PRIMARY KEY,
                    table_name TEXT,
                    content TEXT,
                    metadata JSON
                );
            """)

    def create_table(self, table_name: str, dimension: int) -> None:
        """
        Create a vss table for vectors.
        
        Args:
            table_name: Name of the table.
            dimension: Embedding dimension.
        """
        # vss_table creation
        with self.conn:
            self.conn.execute(f"DROP TABLE IF EXISTS vss_{table_name};")
            self.conn.execute(f"""
                CREATE VIRTUAL TABLE vss_{table_name} USING vss0(
                    embedding({dimension})
                );
            """)
    
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
            table_name: Target logical table.
            doc_id: Document identifier.
            content: Text content.
            embedding: Vector embedding.
            metadata: Optional metadata dict.
        """
        # We store metadata in a regular table and vectors in the virtual table
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO vector_metadata (id, table_name, content, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (doc_id, table_name, content, json.dumps(metadata or {}))
            )
            
            # vss0 rowid must match or we link via the original id
            # For simplicity, we use the rowid from the metadata insert if doc_id isn't integer
            # But vss0 supports explicit rowids. 
            # We'll use the hash of doc_id or just let it auto-increment and manage mapping.
            # Actually, vss virtual tables can't handle non-integer primary keys directly in the same way.
            # Best practice: Insert into vss table with the same rowid as the metadata table.
            
            cursor = self.conn.execute("SELECT rowid FROM vector_metadata WHERE id = ?", (doc_id,))
            rowid = cursor.fetchone()[0]
            
            self.conn.execute(
                f"INSERT INTO vss_{table_name}(rowid, embedding) VALUES (?, ?)",
                (rowid, json.dumps(embedding.tolist()))
            )
    
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
            threshold: Minimum similarity score (converted to distance).
            
        Returns:
            List of matching documents with similarity scores.
        """
        # vss_search returns distance (L2 or similar). 
        # Similarity = 1 / (1 + distance) or similar mapping if needed.
        # But we'll just return distance as 'score' or similar.
        
        query_json = json.dumps(query_embedding.tolist())
        
        try:
            cursor = self.conn.execute(
                f"""
                SELECT 
                    m.id, 
                    m.content, 
                    m.metadata,
                    v.distance
                FROM vss_{table_name} v
                JOIN vector_metadata m ON v.rowid = m.rowid
                WHERE vss_search(v.embedding, vss_search_params(?, ?))
                ORDER BY v.distance ASC
                """,
                (query_json, limit)
            )
            
            results = []
            for row in cursor.fetchall():
                # Convert distance to a pseudo-similarity score [0, 1]
                # Note: vss0 typically uses L2 distance.
                distance = row[3]
                similarity = 1.0 / (1.0 + distance)
                
                if similarity >= threshold:
                    results.append({
                        "id": row[0],
                        "content": row[1],
                        "metadata": json.loads(row[2]),
                        "similarity": round(similarity, 4)
                    })
            
            return results
        except sqlite3.OperationalError as e:
            print(f"Search failed: {e}")
            return []
    
    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
