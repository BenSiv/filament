
import argparse
import os
import sys
import json
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Adjust path to import from scripts directory if running from clean context
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
code_dir = os.path.dirname(current_dir)
if code_dir not in sys.path:
    sys.path.append(code_dir)

try:
    from match_cases import score_pair, normalize_sex, get_date
except ImportError:
    # If match_cases.py is in the same dir but not importable as module
    import importlib.util
    spec = importlib.util.spec_from_file_location("match_cases", os.path.join(current_dir, "match_cases.py"))
    match_cases = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(match_cases)
    score_pair = match_cases.score_pair
    normalize_sex = match_cases.normalize_sex
    get_date = match_cases.get_date

from core.knowledge_note import content_hash, normalize_note, serialize_metadata
from knowledge_review import insert_review

# Hybrid Matcher Configuration
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'filament')
DB_USER = os.getenv('POSTGRES_USER', 'filament')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'filament_dev')

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
        vector_score = lead.get("vector_score", 0)
        reasons = lead.get("reasons", [])
        title = f"Lead: UHR {uhr_id} ↔ MP {mp_id} ({mp_name})"
        reason_lines = "\n- ".join(reasons[:8]) if reasons else "(none)"
        body = (
            f"**UHR Case**: {uhr_id}\n"
            f"**Missing Person**: {mp_name} ({mp_id})\n"
            f"**Composite Score**: {score:.4f}\n"
            f"**Vector Score**: {vector_score:.4f}\n\n"
            f"## Reasons\n- {reason_lines}"
        )
        source_ref = f"{uhr_id}:{mp_id}"
        lead_nid = insert_lead_note(
            cur,
            title,
            body,
            source_ref=source_ref,
            metadata={
                "uhr_case": uhr_id,
                "mp_id": mp_id,
                "score": score,
                "vector_score": vector_score,
                "reasons": reasons[:12],
            },
        )
        qid = log_retrieval(cur, f"match-hybrid:{uhr_id}:{mp_id}")
        uhr_nid = find_note_id(cur, "unidentified", uhr_id)
        mp_nid = find_note_id(cur, "missing_person", mp_id)
        insert_note_link(cur, lead_nid, uhr_nid, "supports", weight=1.0)
        insert_note_link(cur, lead_nid, mp_nid, "supports", weight=1.0)
        log_retrieval_note(cur, qid, uhr_nid, rank=1, score=score, tier_weight=1.0)
        log_retrieval_note(cur, qid, mp_nid, rank=2, score=score, tier_weight=1.0)
        log_review(cur, qid, lead_nid, "candidate", "Lead candidate created from hybrid matcher.")

    conn.commit()
    conn.close()

def get_db():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )
    return conn

def calculate_hybrid_score(uhr_full, mp_full, vector_score, uhr_date_found):
    """
    Combine Vector Similarity with Standard Rule-Based Logic.
    """
    
    # 1. Use the shared scorer from match_cases
    # This handles Date checking, Age, Height, Features, Clothing, Tattoos
    # It returns None if a hard filter is failed (Age mismatch, Date mismatch, etc.)
    result = score_pair(uhr_full, mp_full, uhr_date_found)
    
    if result is None:
        return 0, ["Hard Filter Failed (Logic)"]
        
    rule_score, reasons = result
    
    if rule_score <= 0.1: # Allow low scores but penalize? No, 0 is bad.
        return 0, reasons 

    # 2. Composite
    # Vector score is "Semantic Overlap". Rule score is "Feature Validation".
    # Weighted average: High vector + High rule = Great match.
    final_score = (vector_score * 0.40) + (rule_score * 0.60)
    
    if vector_score > 0.6:
        reasons.insert(0, f"High Semantic Similarity ({vector_score:.2f})")
        
    return final_score, reasons

def main():
    parser = argparse.ArgumentParser(description="Hybrid RAG Matcher")
    parser.add_argument("--fossil-db", default="data/knowledge.fossil", help="Path to Fossil knowledge DB")
    parser.add_argument("--no-fossil-log", action="store_true", help="Disable Fossil logging")
    args = parser.parse_args()

    print("Starting Hybrid RAG Matcher (Consolidated)")
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Get UHR cases (embedding for search, raw_data for scoring)
    print("Fetching UHR cases")
    cursor.execute("""
        SELECT case_number, discovery_date, estimated_sex, raw_data, embedding
        FROM unidentified_cases
        WHERE embedding IS NOT NULL
    """)
    uhr_cases = cursor.fetchall()
    print(f"Loaded {len(uhr_cases)} UHR cases.")
    
    matches = []
    
    print("Matching")
    count = 0
    
    for uhr in uhr_cases:
        if count % 100 == 0:
            print(f"Processed {count}/{len(uhr_cases)}")
        count += 1
        
        uhr_emb = uhr['embedding']
        uhr_raw = uhr['raw_data']
        uhr_sex = normalize_sex(uhr['estimated_sex'])
        uhr_date = get_date(uhr_raw, ['circumstances.dateFound']) # Use helper on raw
        
        # Build Query: KNN + Hard Filters (Sex)
        # Fetch raw_data for MPs to pass to score_pair
        
        sql = """
            SELECT file_number, name, raw_data,
                   1 - (embedding <=> %s::vector) as similarity
            FROM missing_persons
            WHERE embedding IS NOT NULL
        """
        params = [uhr_emb]
        
        # Strict Sex Filter (DB Side)
        if uhr_sex != 'U':
            target_sex = 'Female' if uhr_sex == 'F' else 'Male'
            sql += " AND (sex IS NULL OR sex = 'Unknown' OR sex = 'Uncertain' OR sex = %s)"
            params.append(target_sex)
            
        sql += " ORDER BY embedding <=> %s::vector LIMIT 20"
        params.append(uhr_emb)
        
        cursor.execute(sql, params)
        candidates = cursor.fetchall()
        
        for mp in candidates:
            mp_raw = mp['raw_data']
            vector_score = mp['similarity']
            
            # Extract Narratives for Story Line
            uhr_circ = uhr_raw.get('circumstances', {}).get('circumstancesOfRecovery', '')
            mp_circ = mp_raw.get('circumstances', {}).get('circumstancesOfDisappearance', '')
            
            # Narrative Density Filter (Pre-Score Check)
            # Require at least 20 chars of narrative or rich description
            def is_rich(c): return len(c) > 20
            
            if not is_rich(uhr_circ) and not is_rich(uhr_raw.get('description','')):
                 continue # Skip empty UHRs (or we can just penalize later, but user asked to prefilter)
            
            # Score using shared logic
            score, reasons = calculate_hybrid_score(uhr_raw, mp_raw, vector_score, uhr_date)
            
            # Boost score for Narrative Richness
            if is_rich(uhr_circ) and is_rich(mp_circ):
                score += 0.2
                reasons.append("Rich Narrative Context")
            
            if score > 0.70:
                matches.append({
                    'uhr_id': uhr['case_number'],
                    'mp_id': mp['file_number'],
                    'mp_name': mp['name'],
                    'score': round(float(score), 4),
                    'vector_score': round(float(vector_score), 4),
                    'reasons': reasons,
                    'narratives': {
                        'uhr': uhr_circ[:300] + "" if len(uhr_circ) > 300 else uhr_circ,
                        'mp': mp_circ[:300] + "" if len(mp_circ) > 300 else mp_circ
                    }
                })
                
    matches.sort(key=lambda x: x['score'], reverse=True)
    
    out_file = 'data/processed/leads_hybrid.json'
    with open(out_file, 'w') as f:
        json.dump(matches[:200], f, indent=2)
        
    print(f"Found {len(matches)} matches. Top 200 saved to {out_file}.")

    if matches and not args.no_fossil_log:
        log_leads_to_fossil(matches[:200], args.fossil_db)

if __name__ == "__main__":
    main()
