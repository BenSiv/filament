"""
SQLite-based Graph Store, replacing Neo4j.
"""

import sqlite3
import json
from typing import Any


class GraphClient:
    """
    Client for SQLite-based graph operations.
    
    Usage:
        client = GraphClient(db_path)
        client.create_person(person_entity)
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the SQLite client.
        
        Args:
            db_path: Path to the SQLite database.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._init_schema()
    
    def _init_schema(self) -> None:
        """Initialize nodes and edges tables."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    id TEXT PRIMARY KEY,
                    label TEXT,
                    properties JSON
                );
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_edges (
                    source TEXT,
                    target TEXT,
                    type TEXT,
                    properties JSON,
                    PRIMARY KEY (source, target, type),
                    FOREIGN KEY (source) REFERENCES graph_nodes(id),
                    FOREIGN KEY (target) REFERENCES graph_nodes(id)
                );
            """)

    def close(self):
        """Close the database connection."""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def create_person(self, case_id: str, properties: dict[str, Any]) -> None:
        """
        Create a Person node.
        """
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO graph_nodes (id, label, properties)
                VALUES (?, 'Person', ?)
                """,
                (case_id, json.dumps(properties))
            )
    
    def create_location(self, location_id: str, properties: dict[str, Any]) -> None:
        """
        Create a Location node.
        """
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO graph_nodes (id, label, properties)
                VALUES (?, 'Location', ?)
                """,
                (location_id, json.dumps(properties))
            )
            
    def create_node(self, node_id: str, label: str, properties: dict[str, Any]) -> None:
        """Generic node creation."""
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO graph_nodes (id, label, properties) VALUES (?, ?, ?)",
                (node_id, label, json.dumps(properties))
            )
    
    def link_nodes(
        self, 
        source_id: str, 
        target_id: str, 
        rel_type: str,
        properties: dict[str, Any] | None = None
    ) -> None:
        """Create a relationship between two nodes."""
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO graph_edges (source, target, type, properties)
                VALUES (?, ?, ?, ?)
                """,
                (source_id, target_id, rel_type, json.dumps(properties or {}))
            )

    def link_person_to_location(
        self, 
        case_id: str, 
        location_id: str, 
        relationship: str = "LOCATED_AT"
    ) -> None:
        """
        Compatibility method for previous Neo4j version.
        """
        self.link_nodes(case_id, location_id, relationship)
