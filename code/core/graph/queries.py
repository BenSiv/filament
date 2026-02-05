"""
Graph Query Functions for matching operations.
"""

from typing import Any

from neo4j import GraphDatabase


def find_matches_by_feature(
    driver: GraphDatabase.driver,
    case_id: str,
    similarity_threshold: float = 0.7
) -> list[dict[str, Any]]:
    """
    Find potential matches based on shared physical features.
    
    Args:
        driver: Neo4j driver instance.
        case_id: Case ID of the unidentified person.
        similarity_threshold: Minimum similarity score.
        
    Returns:
        List of match candidates with scores.
    """
    with driver.session() as session:
        result = session.run(
            """
            MATCH (u:Person {case_id: $case_id, type: 'unidentified'})
                  -[:HAS_FEATURE]->(uf:PhysicalFeature)
            MATCH (m:Person {type: 'missing'})
                  -[:HAS_FEATURE]->(mf:PhysicalFeature)
            WHERE u <> m
              AND (uf.medical_term = mf.medical_term 
                   OR uf.category = mf.category)
            WITH u, m, collect(DISTINCT uf.description) AS unid_features,
                 collect(DISTINCT mf.description) AS missing_features
            RETURN m.case_id AS missing_id,
                   m.name AS missing_name,
                   unid_features,
                   missing_features
            """,
            case_id=case_id
        )
        return [dict(record) for record in result]


def find_geographic_proximity(
    driver: GraphDatabase.driver,
    case_id: str,
    max_distance_km: float = 100.0
) -> list[dict[str, Any]]:
    """
    Find missing persons last seen within distance of remains discovery.
    
    Args:
        driver: Neo4j driver instance.
        case_id: Case ID of the unidentified person.
        max_distance_km: Maximum distance in kilometers.
        
    Returns:
        List of geographically proximate missing persons.
    """
    with driver.session() as session:
        result = session.run(
            """
            MATCH (u:Person {case_id: $case_id, type: 'unidentified'})
                  -[:LOCATED_AT]->(ul:Location)
            MATCH (m:Person {type: 'missing'})
                  -[:LAST_SEEN_AT]->(ml:Location)
            WITH u, m, ul, ml,
                 point.distance(
                     point({latitude: ul.lat, longitude: ul.lon}),
                     point({latitude: ml.lat, longitude: ml.lon})
                 ) / 1000.0 AS distance_km
            WHERE distance_km <= $max_distance
            RETURN m.case_id AS missing_id,
                   m.name AS missing_name,
                   ml.name AS last_seen_location,
                   distance_km
            ORDER BY distance_km
            """,
            case_id=case_id,
            max_distance=max_distance_km
        )
        return [dict(record) for record in result]
