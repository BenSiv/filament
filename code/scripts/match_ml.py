
import argparse
import os
import sys
import json
import pickle
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
from sklearn.neighbors import NearestNeighbors
from datetime import datetime

# Add current dir to path to import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
code_dir = os.path.dirname(current_dir)
if code_dir not in sys.path:
    sys.path.append(code_dir)

from train_matching_model import extract_features, FEATURES
from core.knowledge_note import content_hash, normalize_note, serialize_metadata
from knowledge_review import insert_review

# Config
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'filament')
DB_USER = os.getenv('POSTGRES_USER', 'filament')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'filament_dev')
MODEL_PATH = 'data/processed/match_classifier.pkl'

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ai_note(
  nid INTEGER PRIMARY KEY,
  tier INTEGER DEFAULT 0,
  title TEXT,
  body TEXT,
  source_type TEXT,
  source_id INTEGER,
  source_ref TEXT,
  process_level TEXT,
  metadata TEXT,
  artifact_kind TEXT,
  artifact_ref TEXT,
  artifact_rid INTEGER,
  artifact_path TEXT,
  artifact_status TEXT,
  artifact_weight REAL DEFAULT 0.05,
  heat REAL DEFAULT 1.0,
  retrieval_count INTEGER DEFAULT 0,
  last_retrieved_at TEXT,
  content_hash TEXT,
  duplicate_of INTEGER,
  merged_into INTEGER,
  created_at REAL DEFAULT (julianday('now')),
  updated_at REAL DEFAULT (julianday('now'))
);
CREATE TABLE IF NOT EXISTS ai_note_link(
  from_nid INTEGER,
  to_nid INTEGER,
  link_type TEXT,
  weight REAL DEFAULT 1.0,
  updated_at REAL DEFAULT (julianday('now'))
);
CREATE TABLE IF NOT EXISTS ai_retrieval(
  qid INTEGER PRIMARY KEY,
  query_text TEXT,
  created_at REAL DEFAULT (julianday('now'))
);
CREATE TABLE IF NOT EXISTS ai_retrieval_note(
  qid INTEGER,
  nid INTEGER,
  rank INTEGER,
  score REAL,
  tier_weight REAL,
  reinforcement_delta REAL
);
CREATE TABLE IF NOT EXISTS ai_review(
  review_id INTEGER PRIMARY KEY,
  qid INTEGER,
  nid INTEGER,
  atomicity_status TEXT,
  connectivity_status TEXT,
  duplication_status TEXT,
  title_status TEXT,
  promotion_status TEXT,
  action_summary TEXT,
  created_at REAL DEFAULT (julianday('now'))
);
CREATE INDEX IF NOT EXISTS ai_note_content_hash_idx ON ai_note(content_hash);
CREATE INDEX IF NOT EXISTS ai_note_source_type_idx ON ai_note(source_type);
CREATE INDEX IF NOT EXISTS ai_note_source_ref_idx ON ai_note(source_ref);
CREATE INDEX IF NOT EXISTS ai_note_link_from_idx ON ai_note_link(from_nid);
CREATE INDEX IF NOT EXISTS ai_note_link_to_idx ON ai_note_link(to_nid);
CREATE INDEX IF NOT EXISTS ai_retrieval_note_qid_idx ON ai_retrieval_note(qid);
CREATE INDEX IF NOT EXISTS ai_retrieval_note_nid_idx ON ai_retrieval_note(nid);
"""


def find_note_id(cur, source_type, source_ref):
    if not source_ref:
        return None
    cur.execute(
        "SELECT nid FROM ai_note WHERE source_type = ? AND source_ref = ? LIMIT 1",
        (source_type, source_ref),
    )
    row = cur.fetchone()
    return row[0] if row else None


def insert_note_link(cur, from_nid, to_nid, link_type, weight=1.0):
    if not from_nid or not to_nid:
        return
    cur.execute(
        """
        SELECT 1 FROM ai_note_link
        WHERE from_nid = ? AND to_nid = ? AND link_type = ?
        LIMIT 1
        """,
        (from_nid, to_nid, link_type),
    )
    if cur.fetchone():
        return
    cur.execute(
        """
        INSERT INTO ai_note_link(from_nid, to_nid, link_type, weight, updated_at)
        VALUES (?, ?, ?, ?, julianday('now'))
        """,
        (from_nid, to_nid, link_type, weight),
    )


def log_retrieval(cur, query_text):
    cur.execute(
        "INSERT INTO ai_retrieval(query_text, created_at) VALUES (?, julianday('now'))",
        (query_text,),
    )
    return cur.lastrowid


def log_retrieval_note(cur, qid, nid, rank, score=0.0, tier_weight=1.0, reinforcement_delta=0.0):
    if not nid:
        return
    cur.execute(
        """
        INSERT INTO ai_retrieval_note(
            qid, nid, rank, score, tier_weight, reinforcement_delta
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (qid, nid, rank, score, tier_weight, reinforcement_delta),
    )


def log_review(cur, qid, nid, promotion_status, action_summary):
    insert_review(cur, qid, nid, promotion_status, action_summary)


def insert_lead_note(cur, title, body, source_ref, metadata):
    note = normalize_note(
        title=title,
        body=body,
        source_type="lead",
        source_ref=source_ref,
        tier=2,
        metadata=metadata,
        process_level="lead_candidate",
    )
    note_hash = content_hash(note["body"])
    cur.execute("SELECT nid FROM ai_note WHERE content_hash = ? LIMIT 1", (note_hash,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        """
        INSERT INTO ai_note(
            tier, title, body, source_type, source_ref, process_level,
            metadata, artifact_weight, heat, retrieval_count,
            content_hash, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1.0, 0, ?, julianday('now'), julianday('now'))
        """,
        (
            note["tier"],
            note["title"],
            note["body"],
            note["source_type"],
            note["source_ref"],
            note["process_level"],
            serialize_metadata(note["metadata"]),
            0.24,
            note_hash,
        ),
    )
    return cur.lastrowid


def log_leads_to_fossil(leads, fossil_db):
    if not fossil_db or not os.path.exists(fossil_db):
        print(f"Fossil DB not found at {fossil_db}. Skipping Fossil logging.")
        return
    conn = sqlite3.connect(fossil_db)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()

    for lead in leads:
        uhr_id = lead.get("uhr_id")
        mp_id = lead.get("mp_id")
        mp_name = lead.get("mp_name") or "Unknown"
        score = lead.get("score", 0)
        features = lead.get("features", {})
        feature_lines = [f"{k}: {v}" for k, v in list(features.items())[:8]]
        title = f"Lead: UHR {uhr_id} ↔ MP {mp_id} ({mp_name})"
        body = (
            f"**UHR Case**: {uhr_id}\n"
            f"**Missing Person**: {mp_name} ({mp_id})\n"
            f"**Score**: {score:.4f}\n\n"
            f"## Features\n- " + ("\n- ".join(feature_lines) if feature_lines else "(none)")
        )
        source_ref = f"{uhr_id}:{mp_id}"
        lead_nid = insert_lead_note(
            cur,
            title,
            body,
            source_ref=source_ref,
            metadata={"uhr_case": uhr_id, "mp_id": mp_id, "score": score, "features": features},
        )
        qid = log_retrieval(cur, f"match-ml:{uhr_id}:{mp_id}")
        uhr_nid = find_note_id(cur, "unidentified", uhr_id)
        mp_nid = find_note_id(cur, "missing_person", mp_id)
        insert_note_link(cur, lead_nid, uhr_nid, "supports", weight=1.0)
        insert_note_link(cur, lead_nid, mp_nid, "supports", weight=1.0)
        log_retrieval_note(cur, qid, uhr_nid, rank=1, score=score, tier_weight=1.0)
        log_retrieval_note(cur, qid, mp_nid, rank=2, score=score, tier_weight=1.0)
        log_review(cur, qid, lead_nid, "candidate", "Lead candidate created from ML matcher.")

    conn.commit()
    conn.close()

def get_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )

def parse_emb(e):
    if e is None: return None
    return np.array(json.loads(e) if isinstance(e, str) else e)

def main():
    parser = argparse.ArgumentParser(description="Optimized ML Matching Inference (In-Memory)")
    parser.add_argument("--fossil-db", default="data/knowledge.fossil", help="Path to Fossil knowledge DB")
    parser.add_argument("--no-fossil-log", action="store_true", help="Disable Fossil logging")
    args = parser.parse_args()

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

    if matches and not args.no_fossil_log:
        log_leads_to_fossil(matches[:200], args.fossil_db)

if __name__ == "__main__":
    main()
