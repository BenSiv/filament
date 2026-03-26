import argparse
import json
import os
import sqlite3


def main():
    parser = argparse.ArgumentParser(description="Export lead promotion queue")
    parser.add_argument("--db", default="data/knowledge.fossil", help="Path to Fossil DB")
    parser.add_argument("--limit", type=int, default=50, help="Max leads to export")
    parser.add_argument("--out", default="data/reports/promotion_queue.json", help="Output JSON path")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Fossil DB not found: {args.db}")
        return

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT n.nid, n.title, n.source_ref, n.tier, n.process_level,
               n.metadata, n.created_at
        FROM ai_note n
        LEFT JOIN ai_review r ON r.nid = n.nid
        WHERE n.source_type = 'lead'
          AND (r.promotion_status IS NULL OR r.promotion_status IN ('needs_review', 'candidate'))
        ORDER BY n.created_at DESC
        LIMIT ?
        """,
        (args.limit,),
    )

    rows = cur.fetchall()
    queue = []
    for nid, title, source_ref, tier, process_level, metadata, created_at in rows:
        queue.append(
            {
                "nid": nid,
                "title": title,
                "source_ref": source_ref,
                "tier": tier,
                "process_level": process_level,
                "metadata": json.loads(metadata) if metadata else {},
                "created_at": created_at,
            }
        )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(queue, f, indent=2)

    conn.close()
    print(f"Exported {len(queue)} leads to {args.out}")


if __name__ == "__main__":
    main()
