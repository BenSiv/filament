
import json
import os
import sys

# Ensure the code directory is in the path for the filament package
scripts_dir = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.dirname(scripts_dir)
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from core.search import SpecificityMatcher

DB_PATH = "data/filament.db"
OUTPUT_PATH = "data/processed/leads_advanced.json"

def main():
    print("=" * 60)
    print("Advanced Specificity-Based Matcher")
    print("=" * 60)
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    print("Initializing Specificity Matcher")
    matcher = SpecificityMatcher(DB_PATH)
    
    print("Analyzing UHR cases for leads")
    leads = matcher.find_leads(limit=200)
    
    print(f"Found {len(leads)} potential leads.")
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(leads, f, indent=2)
        
    print(f"Top 200 leads saved to {OUTPUT_PATH}")
    
    if leads:
        print("\nTop Lead Discovery:")
        top = leads[0]
        print(f"  {top['uhr_case']} <-> {top['mp_file']} ({top['mp_name']}) [Score: {top['score']}]")

if __name__ == "__main__":
    main()
