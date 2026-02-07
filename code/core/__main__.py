
import sys
import os

# Ensure the code directory is in the path for the core package
core_pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if core_pkg_dir not in sys.path:
    sys.path.insert(0, core_pkg_dir)

from core.search import CompositeMatcher
import json


def main():
    print("=" * 60)
    print("FILAMENT: Forensic Intelligence Linking and Matching")
    print("=" * 60)
    
    db_path = "data/filament.db"
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        print("Please run 'python3 code/scripts/build_sqlite_db.py' first.")
        return

    print("Initializing Composite Matcher")
    matcher = CompositeMatcher(db_path)
    
    output_path = "data/processed/leads_advanced.json"
    leads = []
    
    if os.path.exists(output_path):
        print(f"Loading existing leads from {output_path}")
        with open(output_path, "r") as f:
            leads = json.load(f)
    else:
        print("Discovering advanced leads")
        leads = matcher.find_leads(limit=20)
        
        # Save results for reporting
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(leads, f, indent=2)
        print(f"Leads saved to {output_path}")
    
    print(f"\nFound {len(leads)} investigative leads:")

    # Generate narrative reports for top leads
    print("\nGenerating investigative narrative reports")
    from scripts.generate_narrative_reports import generate_reports
    generate_reports()


if __name__ == "__main__":
    main()
