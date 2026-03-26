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

def ingest_to_fossil():
    reddit_path = os.path.join(root_dir, "data/raw/reddit/missing_and_uhr_narratives.json")
    fossil_db = os.path.join(root_dir, "data/knowledge.fossil")
    fossil_workspace = os.path.join(root_dir, "data/knowledge_workspace")
    
    if not os.path.exists(reddit_path):
        print("Reddit narratives not found. Run scraper first.")
        return
    if not os.path.exists(fossil_db):
        print(f"Fossil repository not found at {fossil_db}")
        print("Initialize it with: fossil init data/knowledge.fossil")
        return

    with open(reddit_path, "r") as f:
        posts = json.load(f)

    print(f"Connecting to Fossil SQLite DB at {fossil_db}")
    conn = sqlite3.connect(fossil_db)
    cur = conn.cursor()

    # Enable AI features directly in the config table
    cur.execute("INSERT OR REPLACE INTO config(name, value, mtime) VALUES('ai-enable','1', strftime('%s','now'))")
    cur.execute("INSERT OR REPLACE INTO config(name, value, mtime) VALUES('agent-provider','ollama', strftime('%s','now'))")
    cur.execute("INSERT OR REPLACE INTO config(name, value, mtime) VALUES('agent-model','qwen3.5:0.8b', strftime('%s','now'))")
    cur.execute("INSERT OR REPLACE INTO config(name, value, mtime) VALUES('agent-embedding-model','nomic-embed-text', strftime('%s','now'))")

    # Create the knowledge-layer tables if they don't exist
    cur.executescript("""
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
    """)

    print(f"Inserting {len(posts)} Reddit narratives as AI Notes...")
    success = 0

    for i, post in enumerate(posts):
        title = f"Reddit: {post.get('title', 'Unknown')[:80]}"
        url = post.get("url", "")
        selftext = post.get("selftext", "")
        body = f"**Source**: {url}\n\n{selftext}"
        note = normalize_note(
            title=title,
            body=body,
            source_type="reddit",
            source_ref=url,
            tier=0,
            metadata={"source_type": "reddit", "url": url, "subreddit": post.get("subreddit", "")},
            process_level="raw",
        )
        note_hash = content_hash(note["body"])

        cur.execute("SELECT 1 FROM ai_note WHERE content_hash = ? LIMIT 1", (note_hash,))
        if cur.fetchone():
            continue

        cur.execute("""
            INSERT INTO ai_note(
                tier, title, body, source_type, source_ref, process_level,
                metadata, artifact_weight, heat, retrieval_count,
                content_hash, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, julianday('now'), julianday('now'))
        """, (
            note["tier"],
            note["title"],
            note["body"],
            note["source_type"],
            note["source_ref"],
            note["process_level"],
            serialize_metadata(note["metadata"]),
            0.05,
            1.0,
            0,
            note_hash,
        ))
        
        success += 1
        if (i + 1) % 25 == 0:
            conn.commit()
            print(f"  Inserted {i+1}/{len(posts)}...")

    conn.commit()
    conn.close()

    print(f"\nSuccessfully wrote {success} Reddit narratives to Fossil AI Knowledge Base.")
    print(f"Repository: {fossil_db}")
    print(f"\nNext steps:")
    print(f"  cd {fossil_workspace}")
    if not os.path.exists(os.path.join(fossil_workspace, ".fslckout")):
        print("  # Warning: workspace not open. Run:")
        print(f"  fossil open {fossil_db} {fossil_workspace}")
    print(f"  fossil agent semantic-index    # Build vector index (requires nomic-embed-text model)")
    print(f"  fossil ui                      # Open browser UI to query via /agentui")

if __name__ == "__main__":
    ingest_to_fossil()
