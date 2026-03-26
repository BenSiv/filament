import argparse
import os
import sqlite3


def _print_section(title):
    print(f"\n{title}")
    print("-" * len(title))


def main():
    parser = argparse.ArgumentParser(description="Fossil knowledge base health report")
    parser.add_argument(
        "--db",
        default="data/knowledge.fossil",
        help="Path to Fossil knowledge database",
    )
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Fossil DB not found: {args.db}")
        return

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    _print_section("Overview")
    cur.execute("SELECT COUNT(*) FROM ai_note")
    print(f"Total notes: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM ai_retrieval")
    print(f"Retrieval events: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM ai_review")
    print(f"Review records: {cur.fetchone()[0]}")

    _print_section("By Tier")
    cur.execute("SELECT tier, COUNT(*) FROM ai_note GROUP BY tier ORDER BY tier")
    for tier, count in cur.fetchall():
        print(f"Tier {tier}: {count}")

    _print_section("By Process Level")
    cur.execute(
        "SELECT process_level, COUNT(*) FROM ai_note GROUP BY process_level ORDER BY COUNT(*) DESC"
    )
    for level, count in cur.fetchall():
        level_display = level or "(null)"
        print(f"{level_display}: {count}")

    _print_section("By Source Type")
    cur.execute(
        "SELECT source_type, COUNT(*) FROM ai_note GROUP BY source_type ORDER BY COUNT(*) DESC"
    )
    for source_type, count in cur.fetchall():
        source_display = source_type or "(null)"
        print(f"{source_display}: {count}")

    _print_section("Lead Notes Without Review")
    cur.execute(
        """
        SELECT COUNT(*)
        FROM ai_note n
        LEFT JOIN ai_review r ON r.nid = n.nid
        WHERE n.source_type = 'lead' AND r.review_id IS NULL
        """
    )
    print(f"Leads missing review: {cur.fetchone()[0]}")

    _print_section("Top Retrieval Queries")
    cur.execute(
        """
        SELECT query_text, COUNT(*)
        FROM ai_retrieval
        GROUP BY query_text
        ORDER BY COUNT(*) DESC
        LIMIT 10
        """
    )
    rows = cur.fetchall()
    if not rows:
        print("(none)")
    else:
        for query_text, count in rows:
            print(f"{query_text}: {count}")

    conn.close()


if __name__ == "__main__":
    main()
