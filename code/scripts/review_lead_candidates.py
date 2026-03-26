import argparse
import os
import sqlite3


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
    parser = argparse.ArgumentParser(description="Seed review records for lead notes")
    parser.add_argument(
        "--db",
        default="data/knowledge.fossil",
        help="Path to Fossil knowledge database",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of lead notes to review (0 = no limit)",
    )
    parser.add_argument(
        "--status",
        default="needs_review",
        help="Promotion status to assign to new reviews",
    )
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Fossil DB not found: {args.db}")
        return

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()

    limit_clause = "" if args.limit <= 0 else f"LIMIT {args.limit}"
    cur.execute(
        f"""
        SELECT n.nid
        FROM ai_note n
        LEFT JOIN ai_review r ON r.nid = n.nid
        WHERE n.source_type = 'lead' AND r.review_id IS NULL
        ORDER BY n.created_at DESC
        {limit_clause}
        """
    )
    rows = cur.fetchall()
    if not rows:
        print("No lead notes found without review.")
        conn.close()
        return

    for (nid,) in rows:
        cur.execute(
            """
            INSERT INTO ai_review(
                qid, nid, atomicity_status, connectivity_status, duplication_status,
                title_status, promotion_status, action_summary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, julianday('now'))
            """,
            (
                None,
                nid,
                "unknown",
                "unknown",
                "unknown",
                "unknown",
                args.status,
                "Seeded review record for lead candidate.",
            ),
        )

    conn.commit()
    print(f"Seeded {len(rows)} review records with status '{args.status}'.")
    conn.close()


if __name__ == "__main__":
    main()
