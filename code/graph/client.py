"""
Neo4j Graph Database Client.
"""

from typing import Any

from neo4j import GraphDatabase


class GraphClient:
    """
    Client for Neo4j graph database operations.
    
    Usage:
        client = GraphClient("bolt://localhost:7687", "neo4j", "password")
        client.create_person(person_entity)
    """
    
    def __init__(self, uri: str, user: str, password: str):
        """
        Initialize the Neo4j client.
        
        Args:
            uri: Neo4j bolt URI.
            user: Database username.
            password: Database password.
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        """Close the database connection."""
        self.driver.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def create_person(self, case_id: str, properties: dict[str, Any]) -> None:
        """
        Create a Person node in the graph.
        
        Args:
            case_id: Unique case identifier.
            properties: Node properties to set.
        """
        with self.driver.session() as session:
            session.run(
                """
                MERGE (p:Person {case_id: $case_id})
                SET p += $props
                """,
                case_id=case_id,
                props=properties
            )
    
    def create_location(self, location_id: str, properties: dict[str, Any]) -> None:
        """
        Create a Location node in the graph.
        
        Args:
            location_id: Unique location identifier.
            properties: Node properties including coordinates.
        """
        with self.driver.session() as session:
            session.run(
                """
                MERGE (l:Location {id: $location_id})
                SET l += $props
                """,
                location_id=location_id,
                props=properties
            )
    
    def link_person_to_location(
        self, 
        case_id: str, 
        location_id: str, 
        relationship: str = "LOCATED_AT"
    ) -> None:
        """
        Create a relationship between a Person and a Location.
        
        Args:
            case_id: Person's case identifier.
            location_id: Location identifier.
            relationship: Type of relationship (LOCATED_AT, LAST_SEEN_AT).
        """
        with self.driver.session() as session:
            session.run(
                f"""
                MATCH (p:Person {{case_id: $case_id}})
                MATCH (l:Location {{id: $location_id}})
                MERGE (p)-[:{relationship}]->(l)
                """,
                case_id=case_id,
                location_id=location_id
            )
