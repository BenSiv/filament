import argparse
import os
import sqlite3


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
"""

REVIEW_COLUMNS = {
    "qid": "INTEGER",
    "nid": "INTEGER",
    "atomicity_status": "TEXT",
    "connectivity_status": "TEXT",
    "duplication_status": "TEXT",
    "title_status": "TEXT",
    "promotion_status": "TEXT",
    "action_summary": "TEXT",
    "created_at": "REAL",
}


def _existing_columns(cur, table):
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def ensure_ai_review_schema(cur):
    existing = _existing_columns(cur, "ai_review")
    for column, col_type in REVIEW_COLUMNS.items():
        if column not in existing:
            cur.execute(f"ALTER TABLE ai_review ADD COLUMN {column} {col_type}")


def main():
    parser = argparse.ArgumentParser(description="Migrate Fossil AI knowledge tables")
    parser.add_argument("--db", default="data/knowledge.fossil", help="Path to Fossil DB")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Fossil DB not found: {args.db}")
        return

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()

    ensure_ai_review_schema(cur)
    conn.commit()
    conn.close()

    print("Migration complete.")


if __name__ == "__main__":
    main()
