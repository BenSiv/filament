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


def _parse_ids(values):
    ids = []
    for value in values:
        if not value:
            continue
        for part in value.split(","):
            part = part.strip()
            if part:
                ids.append(int(part))
    return ids


def main():
    parser = argparse.ArgumentParser(description="Promote lead notes to durable status")
    parser.add_argument("--db", default="data/knowledge.fossil", help="Path to Fossil DB")
    parser.add_argument(
        "--lead-nid",
        action="append",
        default=[],
        help="Lead note id(s) to promote (repeat or comma-separated)",
    )
    parser.add_argument(
        "--source-ref",
        action="append",
        default=[],
        help="Lead source_ref(s) to promote (repeat or comma-separated)",
    )
    parser.add_argument("--tier", type=int, default=3, help="Tier to assign")
    parser.add_argument(
        "--process-level",
        default="promoted",
        help="Process level to assign",
    )
    parser.add_argument(
        "--promotion-status",
        default="promoted",
        help="Promotion status to record",
    )
    parser.add_argument(
        "--artifact-kind",
        default="",
        help="Optional artifact kind (e.g., wiki, file)",
    )
    parser.add_argument(
        "--artifact-path",
        default="",
        help="Optional artifact path (wiki page or file path)",
    )
    parser.add_argument(
        "--artifact-status",
        default="",
        help="Optional artifact status",
    )
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Fossil DB not found: {args.db}")
        return

    lead_ids = _parse_ids(args.lead_nid)
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

    promoted = 0

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
    for nid in unique_ids:
        cur.execute(
            """
            UPDATE ai_note
            SET tier = ?, process_level = ?,
                artifact_kind = COALESCE(NULLIF(?, ''), artifact_kind),
                artifact_path = COALESCE(NULLIF(?, ''), artifact_path),
                artifact_status = COALESCE(NULLIF(?, ''), artifact_status),
                updated_at = julianday('now')
            WHERE nid = ? AND source_type = 'lead'
            """,
            (
                args.tier,
                args.process_level,
                args.artifact_kind,
                args.artifact_path,
                args.artifact_status,
                nid,
            ),
        )
        if cur.rowcount:
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
                    args.promotion_status,
                    f"Promoted lead to tier {args.tier}.",
                ),
            )
            promoted += 1

    conn.commit()
    conn.close()

    print(f"Promoted {promoted} lead note(s).")


if __name__ == "__main__":
    main()
