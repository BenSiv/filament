"""
ingest_all_to_fossil.py
Full ETL pipeline: ingests ALL Filament data into the Fossil AI knowledge base.

Data sources:
  - filament.db: unidentified_cases, missing_persons
  - data/raw/reddit/missing_and_uhr_narratives.json: Reddit sleuth narratives
  - data/reports/reddit_sleuth_leads.json: AI-generated leads

Run this to populate knowledge.fossil, then run:
  cd data/knowledge_workspace && fossil agent semantic-index
"""

import os
import sys
import json
import sqlite3
import hashlib

scripts_dir = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.dirname(scripts_dir)
root_dir = os.path.dirname(code_dir)

FOSSIL_DB = os.path.join(root_dir, "data/knowledge.fossil")
FOSSIL_WORKSPACE = os.path.join(root_dir, "data/knowledge_workspace")
FILAMENT_DB = os.path.join(root_dir, "data/filament.db")
REDDIT_JSON = os.path.join(root_dir, "data/raw/reddit/missing_and_uhr_narratives.json")
LEADS_JSON = os.path.join(root_dir, "data/reports/reddit_sleuth_leads.json")

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
CREATE TABLE IF NOT EXISTS ai_vector(
  vid INTEGER PRIMARY KEY,
  source_type TEXT,
  source_id INTEGER,
  dim INTEGER,
  vector BLOB
);
CREATE INDEX IF NOT EXISTS ai_note_content_hash_idx ON ai_note(content_hash);
CREATE INDEX IF NOT EXISTS ai_note_source_type_idx ON ai_note(source_type);
CREATE INDEX IF NOT EXISTS ai_note_source_ref_idx ON ai_note(source_ref);
"""

def sha1(text):
    return hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()

def insert_note(cur, title, body, source_type, source_ref="", tier=0, metadata=None):
    """Insert a single note, skipping duplicates by content hash."""
    content_hash = sha1(body)
    cur.execute("SELECT 1 FROM ai_note WHERE content_hash = ? LIMIT 1", (content_hash,))
    if cur.fetchone():
        return None
    meta = json.dumps(metadata or {})
    weight = {
        "unidentified": 0.20,
        "missing_person": 0.20,
        "lead": 0.24,
        "reddit": 0.05
    }.get(source_type, 0.05)
    
    cur.execute("""
        INSERT INTO ai_note(
            tier, title, body, source_type, source_ref, process_level,
            metadata, artifact_weight, heat, retrieval_count,
            content_hash, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'raw', ?, ?, 1.0, 0, ?, julianday('now'), julianday('now'))
    """, (tier, title[:200], body, source_type, source_ref, meta, weight, content_hash))
    return cur.lastrowid

def ingest_uhr_cases(fossil_cur, filament_cur, batch=500):
    filament_cur.execute("""
        SELECT case_number, discovery_date, discovery_location_name,
               estimated_age_min, estimated_age_max, estimated_sex,
               race, dna_status, dental_status, description
        FROM unidentified_cases
        WHERE description IS NOT NULL AND length(description) > 30
    """)
    count = 0
    while True:
        rows = filament_cur.fetchmany(batch)
        if not rows:
            break
        for row in rows:
            case_num, date, loc, age_min, age_max, sex, race, dna, dental, desc = row
            age_str = f"~{age_min}-{age_max}" if age_min and age_max else "Unknown"
            title = f"UHR Case {case_num}: {sex or 'Unknown'}, {age_str} yrs, {loc or 'Unknown location'}"
            body = (
                f"**Case Number**: {case_num}\n"
                f"**Discovery Date**: {date or 'Unknown'}\n"
                f"**Location**: {loc or 'Unknown'}\n"
                f"**Estimated Age**: {age_str}\n"
                f"**Sex**: {sex or 'Unknown'} | **Race**: {race or 'Unknown'}\n"
                f"**DNA Status**: {dna or 'Unknown'} | **Dental**: {dental or 'Unknown'}\n\n"
                f"## Case Description\n{desc}"
            )
            insert_note(fossil_cur, title, body, "unidentified", source_ref=case_num,
                        tier=1, metadata={"case_number": case_num, "location": loc})
            count += 1
        fossil_cur.connection.commit()
        print(f"  UHR cases: {count} inserted...")
    print(f"  -> Total UHR cases: {count}")
    return count

def ingest_missing_persons(fossil_cur, filament_cur, batch=500):
    filament_cur.execute("""
        SELECT file_number, name, last_seen_date, last_seen_location_name,
               age_at_disappearance, sex, race, dna_status, dental_status, description
        FROM missing_persons
        WHERE description IS NOT NULL AND length(description) > 30
    """)
    count = 0
    while True:
        rows = filament_cur.fetchmany(batch)
        if not rows:
            break
        for row in rows:
            file_num, name, date, loc, age, sex, race, dna, dental, desc = row
            display_name = name or "Unknown"
            title = f"Missing Person: {display_name} (#{file_num}), {sex or 'Unknown'}, last seen {loc or 'Unknown'}"
            body = (
                f"**File Number**: {file_num}\n"
                f"**Name**: {display_name}\n"
                f"**Last Seen**: {date or 'Unknown'} — {loc or 'Unknown'}\n"
                f"**Age at Disappearance**: {age or 'Unknown'}\n"
                f"**Sex**: {sex or 'Unknown'} | **Race**: {race or 'Unknown'}\n"
                f"**DNA Status**: {dna or 'Unknown'} | **Dental**: {dental or 'Unknown'}\n\n"
                f"## Case Description\n{desc}"
            )
            insert_note(fossil_cur, title, body, "missing_person", source_ref=file_num,
                        tier=1, metadata={"file_number": file_num, "name": display_name})
            count += 1
        fossil_cur.connection.commit()
        print(f"  Missing persons: {count} inserted...")
    print(f"  -> Total missing persons: {count}")
    return count

def ingest_reddit(fossil_cur):
    if not os.path.exists(REDDIT_JSON):
        print("  Reddit narratives file not found, skipping.")
        return 0
    with open(REDDIT_JSON) as f:
        posts = json.load(f)
    count = 0
    for post in posts:
        title = f"Reddit: {post.get('title', 'Unknown')[:90]}"
        url = post.get("url", "")
        selftext = post.get("selftext", "")
        body = f"**Source**: {url}\n\n{selftext}"
        insert_note(fossil_cur, title, body, "reddit", source_ref=url, tier=0,
                    metadata={"url": url, "subreddit": post.get("subreddit", "")})
        count += 1
    fossil_cur.connection.commit()
    print(f"  -> Reddit narratives: {count}")
    return count

def ingest_leads(fossil_cur):
    if not os.path.exists(LEADS_JSON):
        print("  Leads file not found, skipping.")
        return 0
    with open(LEADS_JSON) as f:
        leads = json.load(f)
    count = 0
    for lead in leads:
        case = lead.get("uhr_case", "?")
        reddit_title = lead.get("reddit_title", "?")
        analysis = lead.get("llm_analysis", "")
        score = lead.get("vector_similarity", 0)
        url = lead.get("reddit_url", "")
        title = f"Lead: UHR {case} ↔ {reddit_title[:70]}"
        body = (
            f"**UHR Case**: {case}\n"
            f"**Reddit Thread**: [{reddit_title}]({url})\n"
            f"**Semantic Score**: {score:.2f}\n\n"
            f"## AI Forensic Analysis (qwen3.5:0.8b)\n{analysis}"
        )
        insert_note(fossil_cur, title, body, "lead", source_ref=url, tier=2,
                    metadata={"uhr_case": case, "score": score})
        count += 1
    fossil_cur.connection.commit()
    print(f"  -> AI-generated leads: {count}")
    return count

def main():
    if not os.path.exists(FOSSIL_DB):
        print(f"Fossil repository not found at {FOSSIL_DB}")
        print("Initialize it with: fossil init data/knowledge.fossil")
        return
    if not os.path.exists(FILAMENT_DB):
        print(f"Filament DB not found at {FILAMENT_DB}")
        return
    print(f"Connecting to Fossil: {FOSSIL_DB}")
    fossil_conn = sqlite3.connect(FOSSIL_DB)
    fossil_cur = fossil_conn.cursor()

    # Configure AI features
    for key, val in [
        ("ai-enable", "1"),
        ("agent-provider", "ollama"),
        ("agent-model", "qwen3.5:0.8b"),
        ("agent-embedding-model", "nomic-embed-text"),
    ]:
        fossil_cur.execute(
            "INSERT OR REPLACE INTO config(name, value, mtime) VALUES(?, ?, strftime('%s','now'))",
            (key, val)
        )
    fossil_conn.commit()

    # Ensure schema
    fossil_cur.executescript(SCHEMA_SQL)
    fossil_conn.commit()

    print(f"\nConnecting to Filament DB: {FILAMENT_DB}")
    filament_conn = sqlite3.connect(FILAMENT_DB)
    filament_cur = filament_conn.cursor()

    print("\n[1/4] Ingesting Unidentified Human Remains cases...")
    n_uhr = ingest_uhr_cases(fossil_cur, filament_cur)

    print("\n[2/4] Ingesting Missing Persons cases...")
    n_mp = ingest_missing_persons(fossil_cur, filament_cur)

    print("\n[3/4] Ingesting Reddit sleuth narratives...")
    n_reddit = ingest_reddit(fossil_cur)

    print("\n[4/4] Ingesting AI-generated forensic leads...")
    n_leads = ingest_leads(fossil_cur)

    filament_conn.close()
    fossil_conn.close()

    total = n_uhr + n_mp + n_reddit + n_leads
    print(f"\n✓ Ingestion complete: {total} total records in {FOSSIL_DB}")
    print(f"  UHR cases:      {n_uhr}")
    print(f"  Missing persons:{n_mp}")
    print(f"  Reddit posts:   {n_reddit}")
    print(f"  Leads:          {n_leads}")
    if not os.path.exists(os.path.join(FOSSIL_WORKSPACE, ".fslckout")):
        print("\nWarning: Fossil workspace not open at data/knowledge_workspace.")
        print("Open it with: fossil open data/knowledge.fossil data/knowledge_workspace")
    print(f"\nNext: cd data/knowledge_workspace && fossil agent semantic-index")

if __name__ == "__main__":
    main()
