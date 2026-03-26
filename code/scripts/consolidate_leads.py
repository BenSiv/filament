import argparse
import os
import sqlite3


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ai_note_link(
  from_nid INTEGER,
  to_nid INTEGER,
  link_type TEXT,
  weight REAL DEFAULT 1.0,
  updated_at REAL DEFAULT (julianday('now'))
);
CREATE INDEX IF NOT EXISTS ai_note_link_from_idx ON ai_note_link(from_nid);
CREATE INDEX IF NOT EXISTS ai_note_link_to_idx ON ai_note_link(to_nid);
"""


def insert_note_link(cur, from_nid, to_nid, link_type, weight=1.0):
    if not from_nid or not to_nid:
        return False
    cur.execute(
        """
        SELECT 1 FROM ai_note_link
        WHERE from_nid = ? AND to_nid = ? AND link_type = ?
        LIMIT 1
        """,
        (from_nid, to_nid, link_type),
    )
    if cur.fetchone():
        return False
    cur.execute(
        """
        INSERT INTO ai_note_link(from_nid, to_nid, link_type, weight, updated_at)
        VALUES (?, ?, ?, ?, julianday('now'))
        """,
        (from_nid, to_nid, link_type, weight),
    )
    return True


def main():
    parser = argparse.ArgumentParser(description="Consolidate duplicate lead notes")
    parser.add_argument("--db", default="data/knowledge.fossil", help="Path to Fossil DB")
    parser.add_argument(
        "--min-count",
        type=int,
        default=2,
        help="Minimum duplicates per lead key to link",
    )
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Fossil DB not found: {args.db}")
        return

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()

    cur.execute(
        """
        SELECT source_ref, GROUP_CONCAT(nid), COUNT(*)
        FROM ai_note
        WHERE source_type = 'lead' AND source_ref IS NOT NULL AND source_ref != ''
        GROUP BY source_ref
        HAVING COUNT(*) >= ?
        """,
        (args.min_count,),
    )
    rows = cur.fetchall()
    if not rows:
        print("No duplicate lead groups found.")
        conn.close()
        return

    links_created = 0
    for source_ref, nid_list, count in rows:
        nids = [int(nid) for nid in nid_list.split(",") if nid]
        nids.sort()
        anchor = nids[0]
        for nid in nids[1:]:
            if insert_note_link(cur, anchor, nid, "duplicate_of", weight=1.0):
                links_created += 1

    conn.commit()
    conn.close()

    print(f"Linked {links_created} duplicate lead notes.")


if __name__ == "__main__":
    main()
