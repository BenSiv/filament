"""
Graph Query Functions using SQLite, replacing Neo4j.
"""

import sqlite3
import json
from typing import Any


def find_matches_by_feature(
    conn: sqlite3.Connection,
    case_id: str,
    similarity_threshold: float = 0.7
) -> list[dict[str, Any]]:
    """
    Find potential matches based on shared physical features.
    
    Neo4j Cypher equivalent translated to SQL joins.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            m.id AS missing_id,
            json_extract(m.properties, '$.name') AS missing_name,
            group_concat(DISTINCT json_extract(uf.properties, '$.description')) AS unid_features,
            group_concat(DISTINCT json_extract(mf.properties, '$.description')) AS missing_features
        FROM graph_nodes u
        JOIN graph_edges e1 ON u.id = e1.source AND e1.type = 'HAS_FEATURE'
        JOIN graph_nodes uf ON e1.target = uf.id
        JOIN graph_edges e2 ON uf.id = e2.target AND e2.type = 'HAS_FEATURE'
        JOIN graph_nodes m ON e2.source = m.id
        JOIN graph_edges e3 ON m.id = e3.source AND e3.type = 'HAS_FEATURE'
        JOIN graph_nodes mf ON e3.target = mf.id
        WHERE u.id = ? 
          AND json_extract(u.properties, '$.type') = 'unidentified'
          AND json_extract(m.properties, '$.type') = 'missing'
          AND (
            json_extract(uf.properties, '$.medical_term') = json_extract(mf.properties, '$.medical_term')
            OR json_extract(uf.properties, '$.category') = json_extract(mf.properties, '$.category')
          )
        GROUP BY m.id
        """,
        (case_id,)
    )
    
    results = []
    for row in cursor.fetchall():
        results.append({
            "missing_id": row[0],
            "missing_name": row[1],
            "unid_features": row[2].split(',') if row[2] else [],
            "missing_features": row[3].split(',') if row[3] else []
        })
    return results


def find_geographic_proximity(
    conn: sqlite3.Connection,
    case_id: str,
    max_distance_km: float = 100.0
) -> list[dict[str, Any]]:
    """
    Find missing persons last seen within distance of remains discovery.
    Uses SQLite's json_extract and standard JOINs.
    """
    # Note: SQLite doesn't have a native point.distance. 
    # We use a simplified bounding box or haversine formula if registered as a function.
    # For now, let's assume we fetch and filter in Python or use a simple box.
    
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            m.id AS missing_id,
            json_extract(m.properties, '$.name') AS missing_name,
            json_extract(ml.properties, '$.name') AS last_seen_location,
            json_extract(ul.properties, '$.lat') AS u_lat,
            json_extract(ul.properties, '$.lon') AS u_lon,
            json_extract(ml.properties, '$.lat') AS m_lat,
            json_extract(ml.properties, '$.lon') AS m_lon
        FROM graph_nodes u
        JOIN graph_edges e1 ON u.id = e1.source AND e1.type = 'LOCATED_AT'
        JOIN graph_nodes ul ON e1.target = ul.id
        JOIN graph_nodes ml ON ml.label = 'Location'
        JOIN graph_edges e2 ON ml.id = e2.target AND e2.type = 'LAST_SEEN_AT'
        JOIN graph_nodes m ON e2.source = m.id
        WHERE u.id = ?
          AND json_extract(m.properties, '$.type') = 'missing'
          AND json_extract(u.properties, '$.type') = 'unidentified'
        """,
        (case_id,)
    )
    
    from core.utils.geo_utils import haversine_distance
    
    results = []
    for row in cursor.fetchall():
        m_id, m_name, l_name, u_lat, u_lon, m_lat, m_lon = row
        dist = haversine_distance(u_lat, u_lon, m_lat, m_lon)
        if dist is not None and dist <= max_distance_km:
            results.append({
                "missing_id": m_id,
                "missing_name": m_name,
                "last_seen_location": l_name,
                "distance_km": round(dist, 2)
            })
            
    return sorted(results, key=lambda x: x['distance_km'])
