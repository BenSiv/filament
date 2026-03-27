import argparse
import subprocess
import sys


def _run(cmd):
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description="Run the knowledge pipeline end-to-end")
    parser.add_argument("--skip-reddit", action="store_true", help="Skip reddit lead generation")
    parser.add_argument("--skip-sqlite", action="store_true", help="Skip specificity matcher")
    parser.add_argument("--skip-hybrid", action="store_true", help="Skip hybrid matcher")
    parser.add_argument("--skip-ml", action="store_true", help="Skip ML matcher")
    parser.add_argument("--skip-consolidate", action="store_true", help="Skip lead consolidation")
    parser.add_argument("--skip-review-seed", action="store_true", help="Skip seeding review rows")
    parser.add_argument("--skip-triage", action="store_true", help="Skip triage export")
    parser.add_argument("--fossil-db", default="data/knowledge.fossil", help="Path to Fossil knowledge DB")
    parser.add_argument("--limit", type=int, default=25, help="Lead generation limit (where supported)")
    args = parser.parse_args()

    if not args.skip_reddit:
        _run([
            sys.executable,
            "code/scripts/match_reddit_sleuths.py",
            "--limit",
            str(args.limit),
            "--fossil-db",
            args.fossil_db,
        ])

    if not args.skip_sqlite:
        _run([
            sys.executable,
            "code/scripts/match_sqlite.py",
            "--fossil-db",
            args.fossil_db,
        ])

    if not args.skip_hybrid:
        _run([
            sys.executable,
            "code/scripts/match_hybrid.py",
            "--fossil-db",
            args.fossil_db,
        ])

    if not args.skip_ml:
        _run([
            sys.executable,
            "code/scripts/match_ml.py",
            "--fossil-db",
            args.fossil_db,
        ])

    if not args.skip_consolidate:
        _run([
            sys.executable,
            "code/scripts/consolidate_leads.py",
            "--db",
            args.fossil_db,
        ])

    if not args.skip_review_seed:
        _run([
            sys.executable,
            "code/scripts/review_lead_candidates.py",
            "--db",
            args.fossil_db,
            "--status",
            "needs_review",
        ])

    if not args.skip_triage:
        _run([
            sys.executable,
            "code/scripts/export_promotion_queue.py",
            "--db",
            args.fossil_db,
        ])
        _run([
            sys.executable,
            "code/scripts/generate_triage_report.py",
            "--db",
            args.fossil_db,
        ])

    print("\nPipeline completed.")


if __name__ == "__main__":
    main()
