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

scripts_dir = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.dirname(scripts_dir)
root_dir = os.path.dirname(code_dir)
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from core.knowledge_note import content_hash, normalize_note, serialize_metadata

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
CREATE INDEX IF NOT EXISTS ai_note_link_from_idx ON ai_note_link(from_nid);
CREATE INDEX IF NOT EXISTS ai_note_link_to_idx ON ai_note_link(to_nid);
CREATE INDEX IF NOT EXISTS ai_retrieval_note_qid_idx ON ai_retrieval_note(qid);
CREATE INDEX IF NOT EXISTS ai_retrieval_note_nid_idx ON ai_retrieval_note(nid);
"""

def insert_note(
    cur,
    title,
    body,
    source_type,
    source_ref="",
    tier=0,
    metadata=None,
    process_level="raw",
):
    """Insert a single note, skipping duplicates by content hash."""
    note = normalize_note(
        title=title,
        body=body,
        source_type=source_type,
        source_ref=source_ref,
        tier=tier,
        metadata=metadata,
        process_level=process_level,
    )
    note_hash = content_hash(note["body"])
    cur.execute("SELECT 1 FROM ai_note WHERE content_hash = ? LIMIT 1", (note_hash,))
    if cur.fetchone():
        return None
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1.0, 0, ?, julianday('now'), julianday('now'))
    """, (
        note["tier"],
        note["title"],
        note["body"],
        note["source_type"],
        note["source_ref"],
        note["process_level"],
        serialize_metadata(note["metadata"]),
        weight,
        note_hash,
    ))
    return cur.lastrowid


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
    cur.execute(
        """
        INSERT INTO ai_retrieval_note(
            qid, nid, rank, score, tier_weight, reinforcement_delta
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (qid, nid, rank, score, tier_weight, reinforcement_delta),
    )


def log_review(cur, qid, nid, promotion_status, action_summary):
    cur.execute(
        """
        INSERT INTO ai_review(
            qid, nid, atomicity_status, connectivity_status, duplication_status,
            title_status, promotion_status, action_summary, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, julianday('now'))
        """,
        (qid, nid, "unknown", "unknown", "unknown", "unknown", promotion_status, action_summary),
    )

def ingest_uhr_cases(fossil_cur, filament_cur, batch=500):
    filament_cur.execute("""
        SELECT case_number, discovery_date, discovery_location_name,
               estimated_age_min, estimated_age_max, estimated_sex,
               race, dna_status, dental_status, description
        FROM unidentified_cases
        WHERE description IS NOT NULL AND length(description) > 30
    """)
    count = 0
    note_map = {}
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
            nid = insert_note(
                fossil_cur,
                title,
                body,
                "unidentified",
                source_ref=case_num,
                tier=1,
                metadata={"case_number": case_num, "location": loc},
                process_level="normalized",
            )
            if nid:
                note_map[case_num] = nid
            count += 1
        fossil_cur.connection.commit()
        print(f"  UHR cases: {count} inserted...")
    print(f"  -> Total UHR cases: {count}")
    return count, note_map

def ingest_missing_persons(fossil_cur, filament_cur, batch=500):
    filament_cur.execute("""
        SELECT file_number, name, last_seen_date, last_seen_location_name,
               age_at_disappearance, sex, race, dna_status, dental_status, description
        FROM missing_persons
        WHERE description IS NOT NULL AND length(description) > 30
    """)
    count = 0
    note_map = {}
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
            nid = insert_note(
                fossil_cur,
                title,
                body,
                "missing_person",
                source_ref=file_num,
                tier=1,
                metadata={"file_number": file_num, "name": display_name},
                process_level="normalized",
            )
            if nid:
                note_map[file_num] = nid
            count += 1
        fossil_cur.connection.commit()
        print(f"  Missing persons: {count} inserted...")
    print(f"  -> Total missing persons: {count}")
    return count, note_map

def ingest_reddit(fossil_cur):
    if not os.path.exists(REDDIT_JSON):
        print("  Reddit narratives file not found, skipping.")
        return 0, {}
    with open(REDDIT_JSON) as f:
        posts = json.load(f)
    count = 0
    note_map = {}
    for post in posts:
        title = f"Reddit: {post.get('title', 'Unknown')[:90]}"
        url = post.get("url", "")
        selftext = post.get("selftext", "")
        body = f"**Source**: {url}\n\n{selftext}"
        nid = insert_note(
            fossil_cur,
            title,
            body,
            "reddit",
            source_ref=url,
            tier=0,
            metadata={"url": url, "subreddit": post.get("subreddit", "")},
            process_level="raw",
        )
        if nid:
            note_map[url] = nid
        count += 1
    fossil_cur.connection.commit()
    print(f"  -> Reddit narratives: {count}")
    return count, note_map

def ingest_leads(fossil_cur, uhr_note_map, reddit_note_map):
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
        nid = insert_note(
            fossil_cur,
            title,
            body,
            "lead",
            source_ref=url,
            tier=2,
            metadata={"uhr_case": case, "score": score},
            process_level="lead_candidate",
        )
        if nid:
            qid = log_retrieval(fossil_cur, f"lead:{case}")
            uhr_nid = uhr_note_map.get(case)
            reddit_nid = reddit_note_map.get(url)
            if uhr_nid:
                insert_note_link(fossil_cur, nid, uhr_nid, "supports", weight=1.0)
                log_retrieval_note(fossil_cur, qid, uhr_nid, rank=1, score=1.0, tier_weight=1.0)
            if reddit_nid:
                insert_note_link(fossil_cur, nid, reddit_nid, "supports", weight=1.0)
                log_retrieval_note(fossil_cur, qid, reddit_nid, rank=2, score=score, tier_weight=0.5)
            log_review(fossil_cur, qid, nid, "candidate", "Lead candidate created from retrieval.")
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
    n_uhr, uhr_note_map = ingest_uhr_cases(fossil_cur, filament_cur)

    print("\n[2/4] Ingesting Missing Persons cases...")
    n_mp, _ = ingest_missing_persons(fossil_cur, filament_cur)

    print("\n[3/4] Ingesting Reddit sleuth narratives...")
    n_reddit, reddit_note_map = ingest_reddit(fossil_cur)

    print("\n[4/4] Ingesting AI-generated forensic leads...")
    n_leads = ingest_leads(fossil_cur, uhr_note_map, reddit_note_map)

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
