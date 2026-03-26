
import argparse
import json
import os
import sqlite3
import sys

# Ensure the code directory is in the path for the filament package
scripts_dir = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.dirname(scripts_dir)
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from core.search import SpecificityMatcher
from core.knowledge_note import content_hash, normalize_note, serialize_metadata

DB_PATH = "data/filament.db"
OUTPUT_PATH = "data/processed/leads_advanced.json"

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
    if not nid:
        return
    cur.execute(
        """
        INSERT INTO ai_review(
            qid, nid, atomicity_status, connectivity_status, duplication_status,
            title_status, promotion_status, action_summary, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, julianday('now'))
        """,
        (qid, nid, "unknown", "unknown", "unknown", "unknown", promotion_status, action_summary),
    )


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
        uhr_id = lead.get("uhr_case")
        mp_id = lead.get("mp_file")
        mp_name = lead.get("mp_name") or "Unknown"
        score = lead.get("score", 0)
        features = lead.get("shared_features", [])
        title = f"Lead: UHR {uhr_id} ↔ MP {mp_id} ({mp_name})"
        feature_lines = "\n- ".join(features[:8]) if features else "(none)"
        body = (
            f"**UHR Case**: {uhr_id}\n"
            f"**Missing Person**: {mp_name} ({mp_id})\n"
            f"**Score**: {score:.3f}\n\n"
            f"## Shared Features\n- {feature_lines}"
        )
        source_ref = f"{uhr_id}:{mp_id}"
        lead_nid = insert_lead_note(
            cur,
            title,
            body,
            source_ref=source_ref,
            metadata={"uhr_case": uhr_id, "mp_id": mp_id, "score": score, "features": features[:12]},
        )
        qid = log_retrieval(cur, f"match:{uhr_id}:{mp_id}")
        uhr_nid = find_note_id(cur, "unidentified", uhr_id)
        mp_nid = find_note_id(cur, "missing_person", mp_id)
        insert_note_link(cur, lead_nid, uhr_nid, "supports", weight=1.0)
        insert_note_link(cur, lead_nid, mp_nid, "supports", weight=1.0)
        log_retrieval_note(cur, qid, uhr_nid, rank=1, score=score, tier_weight=1.0)
        log_retrieval_note(cur, qid, mp_nid, rank=2, score=score, tier_weight=1.0)
        log_review(cur, qid, lead_nid, "candidate", "Lead candidate created from specificity matcher.")

    conn.commit()
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Advanced Specificity-Based Matcher")
    parser.add_argument("--fossil-db", default="data/knowledge.fossil", help="Path to Fossil knowledge DB")
    parser.add_argument("--no-fossil-log", action="store_true", help="Disable Fossil logging")
    args = parser.parse_args()

    print("=" * 60)
    print("Advanced Specificity-Based Matcher")
    print("=" * 60)
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    print("Initializing Specificity Matcher")
    matcher = SpecificityMatcher(DB_PATH)
    
    print("Analyzing UHR cases for leads")
    leads = matcher.find_leads(limit=200)
    
    print(f"Found {len(leads)} potential leads.")
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(leads, f, indent=2)
        
    print(f"Top 200 leads saved to {OUTPUT_PATH}")
    
    if leads:
        print("\nTop Lead Discovery:")
        top = leads[0]
        print(f"  {top['uhr_case']} <-> {top['mp_file']} ({top['mp_name']}) [Score: {top['score']}]")

    if leads and not args.no_fossil_log:
        log_leads_to_fossil(leads, args.fossil_db)

if __name__ == "__main__":
    main()
