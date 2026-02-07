
import json
import argparse
import sys
import os
from scrape_doenetwork import init_driver, scrape_cases_batch, convert_jsonl_to_json

IDS_FILE = "data/raw/doenetwork_unidentified_ids.json"
TARGET_FILE = "data/raw/doenetwork_targeted.json"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", default="PA", help="Substring to match in Case ID (e.g. UMPA)")
    args = parser.parse_args()
    
    print(f"Loading IDs from {IDS_FILE}")
    with open(IDS_FILE, 'r') as f:
        all_ids = json.load(f)
        
    targets = {k:v for k,v in all_ids.items() if args.pattern in k}
    print(f"Found {len(targets)} cases matching '{args.pattern}'.")
    
    if not targets:
        print("No targets found.")
        return

    print("Starting Scraper")
    driver = init_driver()
    try:
        jsonl_file = TARGET_FILE.replace('.json', '.jsonl')
        scrape_cases_batch(driver, targets, jsonl_file, resume=True)
        convert_jsonl_to_json(jsonl_file, TARGET_FILE)
        print(f"Saved targeted cases to {TARGET_FILE}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
