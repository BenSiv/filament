
import sys
import os

# Ensure the code directory is in the path for the core package
core_pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if core_pkg_dir not in sys.path:
    sys.path.insert(0, core_pkg_dir)

from core.search import SpecificityMatcher

def main():
    print("=" * 60)
    print("FILAMENT: Forensic Intelligence Linking and Matching")
    print("=" * 60)
    
    db_path = "data/filament.db"
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        print("Please run 'python3 code/scripts/build_sqlite_db.py' first.")
        return

    print("Initializing Specificity Matcher...")
    matcher = SpecificityMatcher(db_path)
    
    print("Discovering advanced leads...")
    leads = matcher.find_leads(limit=20)
    
    print(f"\nFound {len(leads)} top investigative leads:")
    print("-" * 60)
    for i, lead in enumerate(leads, 1):
        features = ", ".join(lead["shared_features"][:3])
        print(f"{i}. [{lead['score']}] {lead['uhr_case']} <-> {lead['mp_file']} ({lead['mp_name']})")
        print(f"   Features: {features}")
    print("-" * 60)

if __name__ == "__main__":
    main()
