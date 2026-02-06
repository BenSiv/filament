
import json
import sqlite3
import os
from pathlib import Path

# Paths relative to project root
DB_PATH = Path("data/filament.db")
UHR_FILE = Path("data/raw/namus_unidentified.json")
MP_FILE = Path("data/raw/namus_missing.json")

def init_db(conn):
    """Initialize the SQLite database with the required schema."""
    cursor = conn.cursor()
    
    # Enable JSON support (built-in for modern SQLite)
    
    # Drop existing tables to ensure clean schema with new columns
    print("Dropping existing tables for clean rebuild...")
    cursor.execute("DROP TABLE IF EXISTS unidentified_cases;")
    cursor.execute("DROP TABLE IF EXISTS missing_persons;")
    
    # Unidentified Cases Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS unidentified_cases (
        id TEXT PRIMARY KEY,
        case_number TEXT UNIQUE NOT NULL,
        source TEXT NOT NULL DEFAULT 'NamUs',
        discovery_date TEXT,
        discovery_location_name TEXT,
        discovery_lat REAL,
        discovery_lon REAL,
        estimated_age_min INTEGER,
        estimated_age_max INTEGER,
        estimated_sex TEXT,
        race TEXT,
        dna_status TEXT,
        dental_status TEXT,
        description TEXT,
        raw_data TEXT, -- JSON string
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Missing Persons Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS missing_persons (
        id TEXT PRIMARY KEY,
        file_number TEXT UNIQUE NOT NULL,
        source TEXT NOT NULL DEFAULT 'NamUs',
        name TEXT,
        last_seen_date TEXT,
        last_seen_location_name TEXT,
        last_seen_lat REAL,
        last_seen_lon REAL,
        age_at_disappearance INTEGER,
        sex TEXT,
        race TEXT,
        dna_status TEXT,
        dental_status TEXT,
        description TEXT,
        raw_data TEXT, -- JSON string
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mp_date_sex ON missing_persons(last_seen_date, sex);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mp_geo ON missing_persons(last_seen_lat, last_seen_lon);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uhr_geo ON unidentified_cases(discovery_lat, discovery_lon);")
    
    conn.commit()
    print(f"Initialized SQLite database at {DB_PATH}")

def get_text_description(obj, c_type='uhr'):
    """Simplified text description for SQLite (matches the original logic)."""
    parts = []
    
    # Sex, Race, Age
    subject_desc = obj.get('subjectDescription', {})
    sex = subject_desc.get('sex', {}).get('name')
    race = subject_desc.get('primaryEthnicity', {}).get('name')
    if not race and 'ethnicities' in subject_desc:
        eths = subject_desc['ethnicities']
        if eths: race = eths[0].get('name')
        
    age = ""
    if c_type == 'uhr':
         min_age = subject_desc.get('estimatedAgeFrom')
         max_age = subject_desc.get('estimatedAgeTo')
         if min_age: age = f"{min_age} to {max_age} years old"
    else:
         age_val = obj.get('subjectIdentification', {}).get('computedMissingMinAge')
         if age_val: age = f"{age_val} years old"
            
    header = f"{sex or 'Unknown'} {race or 'Unknown'} {age}".strip()
    if header: parts.append(header)
    
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
    circ_obj = obj.get('circumstances', {})
    circ = circ_obj.get('circumstancesOfRecovery' if c_type == 'uhr' else 'circumstancesOfDisappearance')
    if circ:
        parts.append(f"Circumstances: {circ}")
        
    return "\n".join(parts)

def load_uhr(conn):
    if not UHR_FILE.exists():
        print(f"Warning: {UHR_FILE} not found.")
        return

    print(f"Loading Unidentified Cases from {UHR_FILE}...")
    with open(UHR_FILE) as f:
        data = json.load(f)
        
    cursor = conn.cursor()
    count = 0
    for case in data:
        case_num = case.get('idFormatted')
        if not case_num: continue
        
        desc = get_text_description(case, 'uhr')
        circ = case.get('circumstances', {})
        discovery_date = circ.get('dateFound')
        
        geo = circ.get('publicGeolocation', {}).get('coordinates', {})
        lat = geo.get('lat')
        lon = geo.get('lon')
        
        # UUID generation or use NamUs ID as primary key? 
        # For simplicity, using idFormatted as unique key and a simple hash/id for PK.
        internal_id = str(case.get('id')) 

        subject_desc = case.get('subjectDescription', {})
        sex = subject_desc.get('sex', {}).get('name')
        race = subject_desc.get('primaryEthnicity', {}).get('name')
        if not race and 'ethnicities' in subject_desc:
            eths = subject_desc['ethnicities']
            if eths: race = eths[0].get('name')
            
        age_min = subject_desc.get('estimatedAgeFrom')
        age_max = subject_desc.get('estimatedAgeTo')
        
        evidence = case.get('evidence', {})
        dna_status = evidence.get('dna')
        dental_status = evidence.get('dental')

        cursor.execute("""
            INSERT OR REPLACE INTO unidentified_cases 
            (id, case_number, source, discovery_date, description, discovery_lat, discovery_lon, 
             estimated_age_min, estimated_age_max, estimated_sex, race, dna_status, dental_status, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            internal_id,
            case_num,
            'NamUs',
            discovery_date,
            desc,
            lat,
            lon,
            age_min,
            age_max,
            sex,
            race,
            dna_status,
            dental_status,
            json.dumps(case)
        ))
        count += 1
    
    conn.commit()
    print(f"Loaded {count} unidentified cases.")

def load_mp(conn):
    if not MP_FILE.exists():
        print(f"Warning: {MP_FILE} not found.")
        return

    print(f"Loading Missing Persons from {MP_FILE}...")
    with open(MP_FILE) as f:
        data = json.load(f)
        
    cursor = conn.cursor()
    count = 0
    for case in data:
        case_num = case.get('idFormatted')
        if not case_num: continue
        
        desc = get_text_description(case, 'mp')
        sighting = case.get('sighting', {})
        last_seen_date = sighting.get('date')
        
        geo = sighting.get('publicGeolocation', {}).get('coordinates', {})
        lat = geo.get('lat')
        lon = geo.get('lon')
        
        ident = case.get('subjectIdentification', {})
        name = f"{ident.get('firstName', '')} {ident.get('lastName', '')}".strip()
        
        internal_id = str(case.get('id'))

        subject_desc = case.get('subjectDescription', {})
        sex = subject_desc.get('sex', {}).get('name')
        race = subject_desc.get('primaryEthnicity', {}).get('name')
        if not race and 'ethnicities' in subject_desc:
            eths = subject_desc['ethnicities']
            if eths: race = eths[0].get('name')

        age = ident.get('computedMissingMinAge')
        
        evidence = case.get('evidence', {})
        dna_status = evidence.get('dna')
        dental_status = evidence.get('dental')

        cursor.execute("""
            INSERT OR REPLACE INTO missing_persons 
            (id, file_number, source, name, last_seen_date, description, last_seen_lat, last_seen_lon, 
             sex, race, dna_status, dental_status, age_at_disappearance, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            internal_id,
            case_num,
            'NamUs',
            name,
            last_seen_date,
            desc,
            lat,
            lon,
            sex,
            race,
            dna_status,
            dental_status,
            age,
            json.dumps(case)
        ))
        count += 1
        
    conn.commit()
    print(f"Loaded {count} missing persons.")

def main():
    # Ensure we are in project root or adjust paths
    os.makedirs("data", exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        load_uhr(conn)
        load_mp(conn)
        print("Success! SQLite database build complete.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
