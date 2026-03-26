import os
import sys
import sqlite3
import json
import numpy as np
import requests
from sentence_transformers import SentenceTransformer

scripts_dir = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.dirname(scripts_dir)
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from core.knowledge_note import content_hash, normalize_note, serialize_metadata

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

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


def find_note_id(cur, source_type, source_ref):
    if not source_ref:
        return None
    cur.execute(
        "SELECT nid FROM ai_note WHERE source_type = ? AND source_ref = ? LIMIT 1",
        (source_type, source_ref),
    )
    row = cur.fetchone()
    return row[0] if row else None


def generate_reddit_leads(limit=50, fossil_db="data/knowledge.fossil", log_to_fossil=True):
    db_path = "data/filament.db"
    reddit_path = "data/raw/reddit/missing_and_uhr_narratives.json"
    
    if not os.path.exists(db_path) or not os.path.exists(reddit_path):
        print("Required data not found. Ensure DB is built and Reddit scraper ran.")
        return
        
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # 1. Load and Embed Reddit Narratives In-Memory (Bypass sqlite-vss)
    with open(reddit_path, "r") as f:
        reddit_posts = json.load(f)
    
    print(f"Embedding {len(reddit_posts)} Reddit narratives...")
    reddit_texts = [f"{p.get('title', '')}\n{p.get('selftext', '')}" for p in reddit_posts]
    reddit_embeddings = model.encode(reddit_texts)
    
    # 2. Get UHR Cases
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT case_number, description 
        FROM unidentified_cases 
        WHERE description IS NOT NULL AND length(description) > 50
        ORDER BY RANDOM() LIMIT ?
    """, (limit,))
    uhr_cases = cur.fetchall()
    conn.close()
    
    fossil_conn = None
    fossil_cur = None
    if log_to_fossil and os.path.exists(fossil_db):
        fossil_conn = sqlite3.connect(fossil_db)
        fossil_cur = fossil_conn.cursor()
        fossil_cur.executescript(SCHEMA_SQL)
        fossil_conn.commit()

    print(f"Executing RAG lead generation for {len(uhr_cases)} UHR cases...")
    leads = []
    
    for i, (case_num, desc) in enumerate(uhr_cases):
        retrieval_qid = None
        if fossil_cur:
            retrieval_qid = log_retrieval(fossil_cur, f"reddit-lead:{case_num}")
        # Embed UHR description
        q_emb = model.encode(desc)
        
        # Calculate similarities
        similarities = [cosine_similarity(q_emb, r_emb) for r_emb in reddit_embeddings]
        
        # Get top 3 indices
        top_indices = np.argsort(similarities)[-3:][::-1]
        
        for rank, idx in enumerate(top_indices, start=1):
            score = similarities[idx]
            if score < 0.35:
                continue
                
            post = reddit_posts[idx]
            title = post.get("title", "")
            print(f"\n[{case_num}] Found sleuth connection in: '{title[:50]}...' (Score: {score:.2f})")
            if fossil_cur and retrieval_qid:
                reddit_nid = find_note_id(fossil_cur, "reddit", post.get("url", ""))
                log_retrieval_note(
                    fossil_cur,
                    retrieval_qid,
                    reddit_nid,
                    rank=rank,
                    score=float(score),
                    tier_weight=0.5,
                )
            
            # Ask Ollama to evaluate the lead
            prompt = f"""
            You are a cold case forensic analyst. An internet sleuth posted a narrative that semantically aligns with an Unidentified Human Remains (UHR) case.
            
            UHR Case {case_num} Details:
            {desc[:800]}
            
            Reddit Sleuth Post: "{title}"
            {post.get("selftext", "")[:1500]}
            
            MISSION:
            Does this Reddit post suggest a viable identity (Missing Person name) or a critical circumstantial connection to this UHR?
            If YES: Provide a brief 2-sentence explanation of the connection.
            If NO: Reply exclusively with the exact string "NO_VIABLE_LEAD".
            """
            
            try:
                response = requests.post(f"http://localhost:11434/api/generate", json={
                    "model": "qwen3.5:0.8b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 300}
                }, timeout=120).json()
                
                analysis = response.get("response", "")
                if not analysis:
                    analysis = response.get("thinking", "NO_VIABLE_LEAD")
                
                if "NO_VIABLE_LEAD" not in analysis:
                    lead = {
                        "uhr_case": case_num,
                        "reddit_url": post.get("url"),
                        "reddit_title": title,
                        "vector_similarity": float(score),
                        "llm_analysis": analysis.strip()
                    }
                    leads.append(lead)
                    if fossil_cur:
                        uhr_nid = find_note_id(fossil_cur, "unidentified", case_num)
                        reddit_nid = find_note_id(fossil_cur, "reddit", post.get("url", ""))
                        lead_title = f"Lead: UHR {case_num} ↔ {title[:70]}"
                        lead_body = (
                            f"**UHR Case**: {case_num}\n"
                            f"**Reddit Thread**: [{title}]({post.get('url')})\n"
                            f"**Semantic Score**: {float(score):.2f}\n\n"
                            f"## AI Forensic Analysis (qwen3.5:0.8b)\n{analysis.strip()}"
                        )
                        lead_nid = insert_lead_note(
                            fossil_cur,
                            lead_title,
                            lead_body,
                            post.get("url", ""),
                            metadata={"uhr_case": case_num, "score": float(score)},
                        )
                        insert_note_link(fossil_cur, lead_nid, uhr_nid, "supports", weight=1.0)
                        insert_note_link(fossil_cur, lead_nid, reddit_nid, "supports", weight=1.0)
                        log_review(
                            fossil_cur,
                            retrieval_qid,
                            lead_nid,
                            "candidate",
                            "Lead candidate created from reddit retrieval.",
                        )
                    print(f"  -> SUCCESS: LLM extracted a narrative lead or identity!")
                else:
                    print(f"  -> Rejected by LLM (No concrete identity/link found).")
            except Exception as e:
                print(f"Error calling LLM: {e}")
        if fossil_conn:
            fossil_conn.commit()
                
    out_dir = "data/reports"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "reddit_sleuth_leads.json")
    
    with open(out_path, "w") as f:
        json.dump(leads, f, indent=2)
        
    print(f"\nGenerated {len(leads)} viable Reddit-based leads. Saved to {out_path}.")
    
    # Generate MD Report
    if leads:
        report_path = os.path.join(out_dir, "reddit_leads_report.md")
        with open(report_path, "w") as f:
            f.write("# Unstructured Narrative (Reddit) Matches\n\n")
            for lead in leads:
                f.write(f"## UHR Case: {lead['uhr_case']}\n")
                f.write(f"- **Thread**: [{lead['reddit_title']}]({lead['reddit_url']})\n")
                f.write(f"- **Semantic Score**: {lead['vector_similarity']:.2f}\n")
                f.write(f"- **AI Analysis**:\n{lead['llm_analysis']}\n\n")
        print(f"Markdown report ready at {report_path}")
    if fossil_conn:
        fossil_conn.commit()
        fossil_conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Number of cases to evaluate")
    parser.add_argument("--fossil-db", default="data/knowledge.fossil", help="Path to Fossil knowledge DB")
    parser.add_argument("--no-fossil-log", action="store_true", help="Disable Fossil logging")
    args = parser.parse_args()
    generate_reddit_leads(args.limit, fossil_db=args.fossil_db, log_to_fossil=not args.no_fossil_log)
