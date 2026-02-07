
import json
import os
import sys
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
import numpy as np

# Configuration
UHR_FILE = 'data/raw/namus_unidentified.json'
MP_FILE = 'data/raw/namus_missing.json'
MODEL_NAME = 'all-MiniLM-L6-v2'
BATCH_SIZE = 100

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'filament'),
        user=os.getenv('POSTGRES_USER', 'filament'),
        password=os.getenv('POSTGRES_PASSWORD', 'filament_dev')
    )

def get_text_description(obj, c_type='uhr'):
    """Create a rich text description for embedding."""
    parts = []
    
    # Sex, Race, Age
    sex = obj.get('subjectDescription', {}).get('sex', {}).get('name')
    race = obj.get('subjectDescription', {}).get('primaryEthnicity', {}).get('name')
    if not race and 'ethnicities' in obj.get('subjectDescription', {}):
        eths = obj['subjectDescription']['ethnicities']
        if eths: race = eths[0].get('name')
        
    age = ""
    if c_type == 'uhr':
         min_age = obj.get('subjectDescription', {}).get('estimatedAgeFrom')
         max_age = obj.get('subjectDescription', {}).get('estimatedAgeTo')
         if min_age: age = f"{min_age} to {max_age} years old"
    else:
         age_val = obj.get('subjectIdentification', {}).get('computedMissingMinAge')
         if age_val: age = f"{age_val} years old"
            
    header = f"{sex or 'Unknown'} {race or 'Unknown'} {age}".strip()
    parts.append(header)
    
    # Features
    feats = [f.get('description') for f in obj.get('physicalFeatureDescriptions', []) if f.get('description')]
    if feats:
        parts.append("Features: " + "; ".join(feats))
        
    if c_type == 'mp':
        tattoos = obj.get('tattoosDescription')
        if tattoos: parts.append(f"Tattoos: {tattoos}")

    # Clothing
    clothes = [c.get('description') for c in obj.get('clothingAndAccessoriesArticles', []) if c.get('description')]
    if clothes:
        parts.append("Clothing: " + "; ".join(clothes))
        
    # Circumstances
    circ = obj.get('circumstances', {}).get('circumstancesOfRecovery' if c_type == 'uhr' else 'circumstancesOfDisappearance')
    if circ:
        parts.append(f"Circumstances: {circ}")
        
    return "\n".join(parts)

def load_uhr(conn, model):
    print(f"Loading UHR from {UHR_FILE}")
    with open(UHR_FILE) as f:
        data = json.load(f)
        
    print(f"Found {len(data)} UHR cases. Processing")
    
    cursor = conn.cursor()
    batch = []
    
    for i, case in enumerate(data):
        case_num = case.get('idFormatted')
        if not case_num: continue
        
        desc = get_text_description(case, 'uhr')
        
        # Prepare subset of fields for DB
        # Note: We keep it simple and store full JSON in raw_data 
        discovery_date = case.get('circumstances', {}).get('dateFound')
        
        # Coordinates
        geo = case.get('circumstances', {}).get('publicGeolocation', {}).get('coordinates', {})
        lat = geo.get('lat')
        lon = geo.get('lon')
        
        batch.append({
            'case_number': case_num,
            'source': 'NamUs',
            'discovery_date': discovery_date,
            'description': desc,
            'lat': lat,
            'lon': lon,
            'raw': json.dumps(case)
        })
        
        if len(batch) >= BATCH_SIZE:
            process_batch_uhr(cursor, batch, model)
            conn.commit()
            batch = []
            print(f"Processed {i+1}/{len(data)} UHRs")
            
    if batch:
        process_batch_uhr(cursor, batch, model)
        conn.commit()

def process_batch_uhr(cursor, batch, model):
    texts = [b['description'] for b in batch]
    embeddings = model.encode(texts)
    
    rows = []
    for i, item in enumerate(batch):
        rows.append((
            item['case_number'],
            item['source'],
            item['discovery_date'],
            item['description'],
            item['lat'],
            item['lon'],
            item['raw'],
            embeddings[i].tolist()
        ))
        
    sql = """
        INSERT INTO unidentified_cases 
        (case_number, source, discovery_date, description, discovery_lat, discovery_lon, raw_data, embedding)
        VALUES %s
        ON CONFLICT (case_number) 
        DO UPDATE SET 
            description = EXCLUDED.description,
            embedding = EXCLUDED.embedding,
            raw_data = EXCLUDED.raw_data;
    """
    execute_values(cursor, sql, rows)

def load_mp(conn, model):
    print(f"Loading MP from {MP_FILE}")
    with open(MP_FILE) as f:
        data = json.load(f)
        
    print(f"Found {len(data)} MP cases. Processing")
    
    cursor = conn.cursor()
    batch = []
    
    for i, case in enumerate(data):
        case_num = case.get('idFormatted')
        if not case_num: continue
        
        desc = get_text_description(case, 'mp')
        
        last_seen_date = case.get('sighting', {}).get('date')
        
        geo = case.get('sighting', {}).get('publicGeolocation', {}).get('coordinates', {})
        lat = geo.get('lat')
        lon = geo.get('lon')
        
        name = f"{case.get('subjectIdentification', {}).get('firstName')} {case.get('subjectIdentification', {}).get('lastName')}"
        
        batch.append({
            'file_number': case_num,
            'source': 'NamUs',
            'name': name,
            'last_seen_date': last_seen_date,
            'description': desc,
            'lat': lat,
            'lon': lon,
            'raw': json.dumps(case)
        })
        
        if len(batch) >= BATCH_SIZE:
            process_batch_mp(cursor, batch, model)
            conn.commit()
            batch = []
            print(f"Processed {i+1}/{len(data)} MPs")
            
    if batch:
        process_batch_mp(cursor, batch, model)
        conn.commit()

def process_batch_mp(cursor, batch, model):
    texts = [b['description'] for b in batch]
    embeddings = model.encode(texts)
    
    rows = []
    for i, item in enumerate(batch):
        rows.append((
            item['file_number'],
            item['source'],
            item['name'],
            item['last_seen_date'],
            item['description'],
            item['lat'],
            item['lon'],
            item['raw'],
            embeddings[i].tolist()
        ))
        
    sql = """
        INSERT INTO missing_persons 
        (file_number, source, name, last_seen_date, description, last_seen_lat, last_seen_lon, raw_data, embedding)
        VALUES %s
        ON CONFLICT (file_number) 
        DO UPDATE SET 
            description = EXCLUDED.description,
            embedding = EXCLUDED.embedding,
            raw_data = EXCLUDED.raw_data;
    """
    execute_values(cursor, sql, rows)

def main():
    print("Initializing Database Loader with RAG Embeddings")
    conn = get_db_connection()
    
    print(f"Loading model {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    
    load_uhr(conn, model)
    load_mp(conn, model)
    
    conn.close()
    print("Done!")

if __name__ == "__main__":
    main()
