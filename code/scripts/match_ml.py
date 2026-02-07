
import os
import sys
import json
import pickle
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
from sklearn.neighbors import NearestNeighbors
from datetime import datetime

# Add current dir to path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from train_matching_model import extract_features, FEATURES

# Config
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'filament')
DB_USER = os.getenv('POSTGRES_USER', 'filament')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'filament_dev')
MODEL_PATH = 'data/processed/match_classifier.pkl'

def get_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )

def parse_emb(e):
    if e is None: return None
    return np.array(json.loads(e) if isinstance(e, str) else e)

def main():
    print("Starting Optimized ML Matching Inference (In-Memory)")
    
    # Load Model
    if not os.path.exists(MODEL_PATH):
        print(f"Model not found at {MODEL_PATH}.")
        return
        
    with open(MODEL_PATH, 'rb') as f:
        clf = pickle.load(f)
    print(f"Loaded classifier.")
    
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Load All MPs
    print("Loading all Missing Persons")
    cursor.execute("""
        SELECT file_number, name, last_seen_date, sex, age_at_disappearance, description, embedding
        FROM missing_persons
        WHERE embedding IS NOT NULL
    """)
    mp_rows = cursor.fetchall()
    
    mp_data = []
    mp_vectors = []
    
    for row in mp_rows:
        vec = parse_emb(row['embedding'])
        if vec is not None:
            mp_vectors.append(vec)
            mp_data.append({
                'last_seen_date': row['last_seen_date'],
                'age_at_disappearance': row['age_at_disappearance'],
                'sex': row['sex'],
                'description': row['description'],
                'embedding': vec, # Keep as array
                'file_number': row['file_number'],
                'name': row['name']
            })
            
    mp_matrix = np.array(mp_vectors)
    print(f"Loaded {len(mp_data)} MPs. Matrix shape: {mp_matrix.shape}")
    
    # 2. Build KNN Index
    print("Building NearestNeighbors Index")
    nbrs = NearestNeighbors(n_neighbors=50, metric='cosine', algorithm='brute')
    nbrs.fit(mp_matrix)
    
    # 3. Load All UHRs
    print("Loading UHR cases")
    cursor.execute("""
        SELECT case_number, discovery_date, estimated_sex, 
               estimated_age_min, estimated_age_max, description, embedding
        FROM unidentified_cases
        WHERE embedding IS NOT NULL
    """)
    uhr_rows = cursor.fetchall()
    print(f"Loaded {len(uhr_rows)} UHR cases.")
    
    matches = []
    
    # 4. Batch Processing
    # We can query all UHRs at once!
    
    uhr_vectors = []
    uhr_data = []
    
    for row in uhr_rows:
        vec = parse_emb(row['embedding'])
        if vec is not None:
            uhr_vectors.append(vec)
            uhr_data.append({
                'discovery_date': row['discovery_date'],
                'estimated_age_min': row['estimated_age_min'],
                'estimated_age_max': row['estimated_age_max'],
                'sex': row['estimated_sex'],
                'description': row['description'],
                'embedding': vec,
                'case_number': row['case_number']
            })
            
    if not uhr_vectors:
        print("No UHR vectors found.")
        return
        
    uhr_matrix = np.array(uhr_vectors)
    print(f"Querying KNN for {uhr_matrix.shape[0]} cases")
    
    # Calculate Distances (batch)
    # n_neighbors=50
    # Note: sklearn returns DISTANCE (cosine distance = 1 - sim).
    # Higher sim = Lower distance.
    distances, indices = nbrs.kneighbors(uhr_matrix)
    
    print("Scoring candidates")
    
    # Process only a subset for demo speed
    uhr_data = uhr_data[:100]
    
    for i, uhr in enumerate(uhr_data):
        neighbor_idxs = indices[i]
        
        # Hard Filter Logic (Sex)
        uhr_sex = uhr['sex']
        
        candidates = []
        for idx in neighbor_idxs:
            mp = mp_data[idx]
            
            # Check Sex Filter
            if uhr_sex in ['M', 'Male'] and mp['sex'] not in ['Male', 'Unknown', 'Uncertain', None]:
                continue
            if uhr_sex in ['F', 'Female'] and mp['sex'] not in ['Female', 'Unknown', 'Uncertain', None]:
                continue
                
            # Date Check? Model handles it, but maybe pre-filter? 
            # Let model handle it.
            candidates.append(mp)
            
        if not candidates: continue
        
        # Extract Features for surviving candidates
        feats_batch = []
        for mp in candidates:
            f = extract_features(uhr, mp)
            feats_batch.append(f)
            
        if not feats_batch: continue
        
        # Bulk Predict
        probs = clf.predict_proba(feats_batch)[:, 1] # Class 1
        
        for j, prob in enumerate(probs):
            if prob > 0.6: # Configurable Threshold
                mp = candidates[j]
                matches.append({
                    'uhr_id': uhr['case_number'],
                    'mp_id': mp['file_number'],
                    'mp_name': mp['name'],
                    'score': round(float(prob), 4),
                    'features': dict(zip(FEATURES, feats_batch[j]))
                })
                
    matches.sort(key=lambda x: x['score'], reverse=True)
    
    out_file = 'data/processed/leads_ml.json'
    with open(out_file, 'w') as f:
        json.dump(matches[:200], f, indent=2)
        
    print(f"Found {len(matches)} ML matches. Top 200 saved to {out_file}.")
    
    print("\nTop 5 ML Matches:")
    for m in matches[:5]:
        print(f"{m['mp_name']} ({m['mp_id']}) <-> {m['uhr_id']}")
        print(f"  Score: {m['score']}")
        print(f"  Features: {m['features']}")

if __name__ == "__main__":
    main()
