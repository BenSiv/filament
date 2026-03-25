import argparse
import sys
import os
import json

def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FILAMENT: Forensic Intelligence Linking and Matching")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Match command
    match_parser = subparsers.add_parser("match", help="Run the matching engine to find leads")
    match_parser.add_argument("--limit", type=int, default=20, help="Number of leads to generate")
    match_parser.add_argument("--db", type=str, default="data/filament.db", help="Path to SQLite DB")
    match_parser.add_argument("--output", type=str, default="data/processed/leads_advanced.json", help="Output JSON path")
    match_parser.add_argument("--min-score", type=float, default=0.35, help="Minimum score threshold")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate Explainable AI (XAI) narrative reports")
    
    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Run data scrapers")
    scrape_parser.add_argument("source", choices=["namus", "reddit", "all"], help="Data source to scrape")
    scrape_parser.add_argument("--limit", type=int, default=100, help="Number of items to fetch per endpoint")
    
    return parser

def cmd_match(args):
    from core.search import CompositeMatcher
    if not os.path.exists(args.db):
        print(f"Error: Database not found at {args.db}")
        sys.exit(1)

    print("Initializing Composite Matcher...")
    matcher = CompositeMatcher(args.db)
    print(f"Discovering advanced leads (limit {args.limit}, min_score {args.min_score})...")
    leads = matcher.find_leads(limit=args.limit, min_score=args.min_score)
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(leads, f, indent=2)
    print(f"Found {len(leads)} leads. Saved to {args.output}")

def cmd_report(args):
    try:
        from scripts.generate_narrative_reports import generate_reports
        print("Generating Explainable AI (XAI) reports...")
        generate_reports()
    except ImportError as e:
        print(f"Error loading report generator: {e}")

def cmd_scrape(args):
    print(f"Running scraper for source: {args.source} with limit: {args.limit}")
    if args.source == "reddit":
        try:
            from core.scrapers.reddit import scrape_reddit_narratives
            scrape_reddit_narratives(limit=args.limit)
        except ImportError:
            print("Error: Reddit scraper not found/implemented yet.")
    else:
        print(f"Scraper for {args.source} is not fully wired to CLI yet.")

def main():
    parser = setup_parser()
    args = parser.parse_args()
    
    if args.command == "match":
        cmd_match(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "scrape":
        cmd_scrape(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
