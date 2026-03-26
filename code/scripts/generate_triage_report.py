import argparse
import json
import os
import sqlite3


def main():
    parser = argparse.ArgumentParser(description="Generate triage report for lead candidates")
    parser.add_argument("--db", default="data/knowledge.fossil", help="Path to Fossil DB")
    parser.add_argument("--limit", type=int, default=50, help="Max leads to include")
    parser.add_argument("--out", default="data/reports/lead_triage_report.md", help="Output markdown path")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Fossil DB not found: {args.db}")
        return

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT n.nid, n.title, n.source_ref, n.process_level, n.metadata,
               n.created_at, r.promotion_status
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
    conn.close()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write("# Lead Triage Queue\n\n")
        f.write(f"Total Leads: {len(rows)}\n\n")
        for idx, row in enumerate(rows, start=1):
            nid, title, source_ref, process_level, metadata, created_at, status = row
            meta = json.loads(metadata) if metadata else {}
            score = meta.get("score", "")
            uhr_case = meta.get("uhr_case", "")
            mp_id = meta.get("mp_id", meta.get("mp_file", ""))
            f.write(f"## {idx}. {title}\n")
            f.write(f"- **Lead ID**: {nid}\n")
            if uhr_case:
                f.write(f"- **UHR Case**: {uhr_case}\n")
            if mp_id:
                f.write(f"- **MP ID**: {mp_id}\n")
            if source_ref:
                f.write(f"- **Source Ref**: {source_ref}\n")
            if score != "":
                f.write(f"- **Score**: {score}\n")
            f.write(f"- **Process Level**: {process_level}\n")
            f.write(f"- **Review Status**: {status or 'needs_review'}\n")
            f.write(f"- **Created At**: {created_at}\n\n")

    print(f"Triage report written to {args.out}")


if __name__ == "__main__":
    main()
