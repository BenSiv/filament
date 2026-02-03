
import json
import os
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer

# Reuse logic
from load_namus_to_db import get_text_description, get_db_connection

MODEL_NAME = 'all-MiniLM-L6-v2'

def main():
    print("Loading specific cases...")
    conn = get_db_connection()
    model = SentenceTransformer(MODEL_NAME)
    cursor = conn.cursor()
    
    # Load UHR 77011
    with open('data/raw/namus_unidentified.json') as f:
        uhr_data = json.load(f)
        
    target_uhr = next((c for c in uhr_data if str(c.get('id', '')) == '77011' or c.get('idFormatted') == 'UP77011'), None)
    if target_uhr:
        print(f"Found UHR 77011. Inserting...")
        desc = get_text_description(target_uhr, 'uhr')
        emb = model.encode(desc).tolist()
        
        sql = """
            INSERT INTO unidentified_cases 
            (case_number, source, discovery_date, description, raw_data, embedding)
            VALUES %s
            ON CONFLICT (case_number) 
            DO UPDATE SET description = EXCLUDED.description, embedding = EXCLUDED.embedding, raw_data = EXCLUDED.raw_data;
        """
        cursor.execute(sql, [(
            target_uhr['idFormatted'], 'NamUs', 
            target_uhr.get('circumstances', {}).get('dateFound'),
            desc, json.dumps(target_uhr), emb
        )])
        conn.commit()
    else:
        print("UHR 77011 not found in JSON.")

    # Load MP 28312
    with open('data/raw/namus_missing.json') as f:
        mp_data = json.load(f)
        
    target_mp = next((c for c in mp_data if str(c.get('id', '')) == '28312' or c.get('idFormatted') == 'MP28312'), None)
    if target_mp:
        print(f"Found MP 28312. Inserting...")
        desc = get_text_description(target_mp, 'mp')
        emb = model.encode(desc).tolist()
        name = f"{target_mp.get('subjectIdentification', {}).get('firstName')} {target_mp.get('subjectIdentification', {}).get('lastName')}"
        
        sql = """
            INSERT INTO missing_persons 
            (file_number, source, name, last_seen_date, description, raw_data, embedding)
            VALUES %s
            ON CONFLICT (file_number) 
            DO UPDATE SET description = EXCLUDED.description, embedding = EXCLUDED.embedding, raw_data = EXCLUDED.raw_data;
        """
        cursor.execute(sql, [(
            target_mp['idFormatted'], 'NamUs', name,
            target_mp.get('sighting', {}).get('date'),
            desc, json.dumps(target_mp), emb
        )])
        conn.commit()
    else:
        print("MP 28312 not found in JSON.")
        
    conn.close()

if __name__ == "__main__":
    main()
