import argparse
import os
import sqlite3
import sys

scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from knowledge_review import insert_review


SCHEMA_SQL = """
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


def main():
    parser = argparse.ArgumentParser(description="Update review status for lead notes")
    parser.add_argument("--db", default="data/knowledge.fossil", help="Path to Fossil DB")
    parser.add_argument(
        "--lead-nid",
        action="append",
        default=[],
        help="Lead note id(s) to update (repeat or comma-separated)",
    )
    parser.add_argument(
        "--source-ref",
        action="append",
        default=[],
        help="Lead source_ref(s) to update (repeat or comma-separated)",
    )
    parser.add_argument(
        "--promotion-status",
        default="reviewed",
        help="Promotion status to set (e.g., needs_review, candidate, promoted, rejected)",
    )
    parser.add_argument(
        "--summary",
        default="Review decision recorded.",
        help="Action summary to store",
    )
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Fossil DB not found: {args.db}")
        return

    lead_ids = []
    for value in args.lead_nid:
        if not value:
            continue
        for part in value.split(","):
            part = part.strip()
            if part:
                lead_ids.append(int(part))

    source_refs = []
    for value in args.source_ref:
        if not value:
            continue
        source_refs.extend([part.strip() for part in value.split(",") if part.strip()])

    if not lead_ids and not source_refs:
        print("No leads specified. Use --lead-nid or --source-ref.")
        return

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()

    if source_refs:
        cur.execute(
            f"""
            SELECT nid FROM ai_note
            WHERE source_type = 'lead' AND source_ref IN ({','.join('?' for _ in source_refs)})
            """,
            source_refs,
        )
        lead_ids.extend([row[0] for row in cur.fetchall()])

    unique_ids = sorted(set(lead_ids))
    updated = 0
    for nid in unique_ids:
        insert_review(cur, None, nid, args.promotion_status, args.summary)
        if cur.rowcount:
            updated += 1

    conn.commit()
    conn.close()

    print(f"Recorded review status for {updated} lead note(s).")


if __name__ == "__main__":
    main()
