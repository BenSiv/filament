#!/usr/bin/env python3
"""
Load BC UHR Data into PostgreSQL with Vector Embeddings

This script:
1. Loads the raw UHR JSON data
2. Generates text embeddings for semantic search
3. Inserts into PostgreSQL with pgvector
"""

import json
import os
import sys
from datetime import datetime

# Database connection
import psycopg2
from psycopg2.extras import execute_values

# For embeddings - we'll use a simple approach first
# In production, use sentence-transformers

def get_db_connection():
    """Get PostgreSQL connection from environment or defaults."""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'filament'),
        user=os.getenv('POSTGRES_USER', 'filament'),
        password=os.getenv('POSTGRES_PASSWORD', 'filament_dev')
    )


def create_description(case: dict) -> str:
    """Create a searchable text description from case attributes."""
    parts = []
    
    # Basic info
    if case.get('Sex'):
        parts.append(f"{case['Sex']}")
    
    age_min = case.get('Minimum_Ag')
    age_max = case.get('Maximum_Ag')
    if age_min and age_max:
        parts.append(f"aged {int(age_min)}-{int(age_max)}")
    
    if case.get('Race') and case['Race'] != 'Unknown':
        parts.append(case['Race'])
    
    # Physical description
    if case.get('Hair_Colou') and case['Hair_Colou'].strip():
        parts.append(f"{case['Hair_Colou']} hair")
    
    if case.get('Eye_Colour') and case['Eye_Colour'].strip():
        parts.append(f"{case['Eye_Colour']} eyes")
    
    height_min = case.get('Minimum_He')
    height_max = case.get('Maximum_He')
    if height_min and height_min.strip():
        parts.append(f"height {height_min}")
    
    # Clothing
    if case.get('Clothing') and case['Clothing'].strip():
        parts.append(f"wearing: {case['Clothing']}")
    
    # Identifying features
    if case.get('Tattoos') and case['Tattoos'].strip():
        parts.append(f"tattoos: {case['Tattoos']}")
    
    if case.get('Scars') and case['Scars'].strip():
        parts.append(f"scars: {case['Scars']}")
    
    if case.get('Other_Comm') and case['Other_Comm'].strip():
        parts.append(case['Other_Comm'])
    
    return '. '.join(parts) if parts else ''


def epoch_to_date(epoch_ms):
    """Convert epoch milliseconds to date string."""
    if epoch_ms:
        try:
            return datetime.fromtimestamp(epoch_ms / 1000).strftime('%Y-%m-%d')
        except:
            pass
    return None


def load_uhr_data(conn, json_path: str):
    """Load UHR cases into the database."""
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    cases = [feat['attributes'] for feat in data['features']]
    print(f"Loading {len(cases)} cases...")
    
    # Prepare data for insertion
    rows = []
    for case in cases:
        description = create_description(case)
        
        row = (
            case.get('Case_Numbe'),
            'BCCS',  # source
            epoch_to_date(case.get('Date_Found')),
            case.get('Latitude'),
            case.get('Longitude'),
            f"Near {case.get('Latitude'):.2f}°N, {abs(case.get('Longitude')):.2f}°W" if case.get('Latitude') else None,
            int(case.get('Minimum_Ag')) if case.get('Minimum_Ag') else None,
            int(case.get('Maximum_Ag')) if case.get('Maximum_Ag') else None,
            case.get('Sex'),
            None,  # height_cm_min - would need conversion from ft
            None,  # height_cm_max
            None,  # weight_kg_min
            None,  # weight_kg_max
            False,  # dna_available - not in source
            False,  # dental_available
            description,
            json.dumps(case),  # raw_data
        )
        rows.append(row)
    
    # Insert into database
    with conn.cursor() as cur:
        # Clear existing BCCS data
        cur.execute("DELETE FROM unidentified_cases WHERE source = 'BCCS'")
        
        # Insert new data
        insert_sql = """
            INSERT INTO unidentified_cases (
                case_number, source, discovery_date,
                discovery_lat, discovery_lon, discovery_location_name,
                estimated_age_min, estimated_age_max, estimated_sex,
                height_cm_min, height_cm_max, weight_kg_min, weight_kg_max,
                dna_available, dental_available,
                description, raw_data
            ) VALUES %s
            ON CONFLICT (case_number) DO UPDATE SET
                description = EXCLUDED.description,
                raw_data = EXCLUDED.raw_data,
                updated_at = NOW()
        """
        
        execute_values(cur, insert_sql, rows)
        conn.commit()
        
        print(f"Inserted {len(rows)} cases")
        
        # Verify
        cur.execute("SELECT COUNT(*) FROM unidentified_cases WHERE source = 'BCCS'")
        count = cur.fetchone()[0]
        print(f"Total BCCS cases in database: {count}")


def load_clothing_data(conn, json_path: str):
    """Load clothing items as separate records."""
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    cases = [feat['attributes'] for feat in data['features']]
    
    with conn.cursor() as cur:
        clothing_count = 0
        
        for case in cases:
            clothing_text = case.get('Clothing', '').strip()
            if not clothing_text:
                continue
            
            # Get case ID
            cur.execute(
                "SELECT id FROM unidentified_cases WHERE case_number = %s",
                (case['Case_Numbe'],)
            )
            result = cur.fetchone()
            if not result:
                continue
            
            case_id = result[0]
            
            # Insert clothing record
            cur.execute("""
                INSERT INTO clothing (case_id, item_type, description)
                VALUES (%s, 'ensemble', %s)
                ON CONFLICT DO NOTHING
            """, (case_id, clothing_text))
            clothing_count += 1
        
        conn.commit()
        print(f"Inserted {clothing_count} clothing records")


def main():
    print("=" * 60)
    print("Loading BC UHR Data into PostgreSQL")
    print("=" * 60)
    
    json_path = 'data/raw/bc_uhr_cases.json'
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        print("Run the data fetch script first")
        sys.exit(1)
    
    try:
        conn = get_db_connection()
        print("Connected to PostgreSQL")
        
        # Check pgvector extension
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
            if cur.fetchone():
                print("pgvector extension: OK")
            else:
                print("WARNING: pgvector extension not installed")
        
        # Load data
        load_uhr_data(conn, json_path)
        load_clothing_data(conn, json_path)
        
        # Show sample
        print()
        print("Sample loaded data:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT case_number, estimated_sex, estimated_age_min, estimated_age_max,
                       LEFT(description, 80) as description_preview
                FROM unidentified_cases
                WHERE source = 'BCCS'
                LIMIT 3
            """)
            for row in cur.fetchall():
                print(f"  {row[0]}: {row[1]}, {row[2]}-{row[3]}yo")
                print(f"    {row[4]}...")
        
        conn.close()
        print()
        print("Data loading complete!")
        
    except psycopg2.OperationalError as e:
        print(f"Database connection failed: {e}")
        print("Make sure PostgreSQL container is running:")
        print("  podman ps | grep filament-postgres")
        sys.exit(1)


if __name__ == '__main__':
    main()
