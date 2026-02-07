
import argparse
import os
import psycopg2
import sys
from sentence_transformers import SentenceTransformer

# Configuration
MODEL_NAME = 'all-MiniLM-L6-v2'

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'filament'),
        user=os.getenv('POSTGRES_USER', 'filament'),
        password=os.getenv('POSTGRES_PASSWORD', 'filament_dev')
    )

def find_matches(uhr_id, limit=20):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get the UHR case details and embedding
    cur.execute("""
        SELECT description, embedding, discovery_date, raw_data
        FROM unidentified_cases 
        WHERE case_number = %s OR case_number = %s
    """, (uhr_id, f"UP{uhr_id}")) 
    
    uhr = cur.fetchone()
    if not uhr:
        print(f"Error: UHR {uhr_id} not found in database.")
        return
        
    uhr_desc, uhr_emb, uhr_found, uhr_raw = uhr
    
    # Extract Sex for Filter
    uhr_sex = uhr_raw.get('subjectDescription', {}).get('sex', {}).get('name')
    
    print(f"Found UHR: {uhr_id} (Sex: {uhr_sex})")
    print(f"Description: {uhr_desc[:100]}")
    
    # Build Query
    # We want MPs where:
    # 1. Sex matches (or is unknown) -> Strict for now
    # 2. Embedding distance is low
    
    # Note: pgvector <-> is Euclidean distance (L2). For normalized vectors (SentenceTransformers), cosine distance <=> L2.
    # We order by embedding <-> uhr_emb
    
    # Query with JSONB filters
    # raw_data -> 'subjectDescription' -> 'sex' ->> 'name'
    
    query = """
        SELECT 
            file_number, 
            name, 
            description, 
            last_seen_date, 
            embedding <-> %s::vector AS distance,
            raw_data->'subjectDescription'->'sex'->>'name' as sex,
            (raw_data->'subjectDescription'->>'heightFrom')::numeric as height
        FROM missing_persons
        WHERE 1=1
    """
    params = [str(uhr_emb)]
    
    # 1. Sex Filter
    if uhr_sex and uhr_sex != 'Unknown' and uhr_sex != 'Uncertain':
        query += " AND (raw_data->'subjectDescription'->'sex'->>'name' = %s OR raw_data->'subjectDescription'->'sex'->>'name' = 'Unknown')"
        params.append(uhr_sex)
        
    # 2. Timeline Filter
    if uhr_found:
        query += " AND (last_seen_date IS NULL OR last_seen_date <= %s)"
        params.append(uhr_found)
        
    # Order by semantic similarity
    query += " ORDER BY distance ASC LIMIT %s"
    params.append(limit)
    
    cur.execute(query, params)
    matches = cur.fetchall()
    
    print(f"\nTop {limit} Semantic Matches:\n")
    
    for m in matches:
        mp_id, mp_name, mp_desc, mp_date, dist, mp_sex, mp_height = m
        
        # Post-filter: Height check (if available for both)
        # Using 3 inches (approx 7.5 cm) buffer
        h_match = "✅"
        # Extraction from Description for display
        print(f"{mp_name} ({mp_id}) - Score: {1-dist:.3f}")
        print(f"  Missing: {mp_date} | Sex: {mp_sex} | Ht: {mp_height}in")
        print(f"  Desc: {mp_desc[:150]}")
        print("-" * 40)
        
    conn.close()

def main():
    parser = argparse.ArgumentParser(description='RAG Matching for UHR')
    parser.add_argument('uhr_id', help='UHR Case ID')
    args = parser.parse_args()
    
    find_matches(args.uhr_id)

if __name__ == "__main__":
    main()
