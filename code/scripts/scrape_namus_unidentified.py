#!/usr/bin/env python3
"""
NamUs Unidentified Persons API Scraper

Uses the NamUs public JSON API to fetch all unidentified person cases.
API endpoints discovered:
  - POST /api/CaseSets/NamUs/UnidentifiedPersons/Search (search/list)
  - GET  /api/CaseSets/NamUs/UnidentifiedPersons/Cases/{id} (case details)

The search API has a 10,000 result limit, so we query by state to get full coverage.
"""

import json
import time
import argparse
import os
from datetime import datetime
import requests

# Configuration
BASE_URL = "https://www.namus.gov"
SEARCH_ENDPOINT = f"{BASE_URL}/api/CaseSets/NamUs/UnidentifiedPersons/Search"
CASE_ENDPOINT = f"{BASE_URL}/api/CaseSets/NamUs/UnidentifiedPersons/Cases"
OUTPUT_FILE = "data/raw/namus_unidentified.json"
OUTPUT_JSONL = "data/raw/namus_unidentified.jsonl"

# US States for chunked queries (to bypass 10K limit)
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming", "District of Columbia",
    "Puerto Rico", "Guam", "Virgin Islands"
]

# Standard headers for API requests (must match browser exactly)
HEADERS = {
    "Content-Type": "application/json;charset=utf-8",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.namus.gov/UnidentifiedPersons/Search",
    "Origin": "https://www.namus.gov"
}


def search_cases(session, state=None, take=100, skip=0):
    """
    Search for unidentified person cases using the NamUs API.
    
    Args:
        session: requests.Session object
        state: Optional state name to filter by
        take: Number of results per request (max 100)
        skip: Pagination offset
    
    Returns:
        dict with 'count' and 'results' keys
    """
    # Use exact field names from NamUs API (captured from browser)
    payload = {
        "take": take,
        "skip": skip,
        "projections": [
            "idFormatted",
            "caseNumber",
            "dateFound",
            "estimatedAgeFrom",
            "estimatedAgeTo",
            "cityOfRecovery",
            "countyDisplayNameOfRecovery",
            "stateOfRecovery",
            "sex",
            "raceEthnicity",
            "modifiedDateTime",
            "namus2Number",
            "stateDisplayNameOfRecovery"
        ],
        "predicates": [],
        "orderSpecifications": [
            {"field": "dateFound", "direction": "Descending"}
        ]
    }
    
    # Add state filter if specified
    if state:
        payload["predicates"].append({
            "field": "stateOfRecovery",
            "operator": "IsIn",
            "values": [state]
        })
    
    try:
        resp = session.post(SEARCH_ENDPOINT, json=payload, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"Error searching cases: {e}")
        return {"count": 0, "results": []}


def get_case_details(session, case_id):
    """
    Fetch full details for a specific case.
    
    Args:
        session: requests.Session object
        case_id: Numeric case ID
    
    Returns:
        dict with case details or None on error
    """
    url = f"{CASE_ENDPOINT}/{case_id}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"Error fetching case {case_id}: {e}")
        return None


def collect_all_case_ids(session, by_state=True):
    """
    Collect all case IDs from NamUs.
    
    Args:
        session: requests.Session object
        by_state: If True, query by state to bypass 10K limit
    
    Returns:
        list of case summary dicts
    """
    all_cases = []
    
    if by_state:
        # Query each state separately to bypass 10K limit
        for state in US_STATES:
            print(f"Fetching cases for {state}")
            skip = 0
            state_count = 0
            
            while True:
                result = search_cases(session, state=state, take=100, skip=skip)
                cases = result.get("results", [])
                
                if not cases:
                    break
                
                all_cases.extend(cases)
                state_count += len(cases)
                skip += 100
                
                # Small delay to be respectful
                time.sleep(0.2)
            
            print(f"  -> {state_count} cases")
    else:
        # Single query (limited to 10K)
        print("Fetching all cases (may be limited to 10K)")
        skip = 0
        
        while True:
            result = search_cases(session, take=100, skip=skip)
            cases = result.get("results", [])
            
            if not cases:
                break
            
            all_cases.extend(cases)
            skip += 100
            
            if skip % 1000 == 0:
                print(f"  Fetched {skip} cases")
            
            if skip >= 10000:
                print("  Warning: Reached 10K limit. Use --by-state for full data.")
                break
            
            time.sleep(0.2)
    
    return all_cases


def fetch_case_details_batch(session, case_summaries, output_file, resume=True):
    """
    Fetch full details for all cases and save incrementally.
    
    Args:
        session: requests.Session object
        case_summaries: list of case summary dicts (must have 'id' field)
        output_file: JSONL file to write to
        resume: If True, skip already processed cases
    """
    # Load already processed IDs if resuming
    processed_ids = set()
    if resume and os.path.exists(output_file):
        with open(output_file, 'r') as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if 'id' in rec:
                        processed_ids.add(rec['id'])
                except json.JSONDecodeError:
                    pass
        print(f"Resuming... {len(processed_ids)} cases already processed.")
    
    total = len(case_summaries)
    fetched = 0
    
    with open(output_file, 'a') as f:
        for i, summary in enumerate(case_summaries):
            # Use namus2Number as the case ID (that's what's in summaries)
            case_id = summary.get('namus2Number') or summary.get('id')
            
            if not case_id or case_id in processed_ids:
                continue
            
            details = get_case_details(session, case_id)
            
            if details:
                f.write(json.dumps(details) + "\n")
                f.flush()
                fetched += 1
            
            if (i + 1) % 50 == 0:
                print(f"Progress: {i+1}/{total} ({fetched} new details fetched)")
            
            time.sleep(0.3)  # Be respectful to the server
    
    return fetched


def convert_jsonl_to_json(jsonl_file, json_file):
    """Convert JSONL file to pretty-printed JSON array."""
    records = []
    with open(jsonl_file, 'r') as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    
    with open(json_file, 'w') as f:
        json.dump(records, f, indent=2)
    
    return len(records)


def test_api(session):
    """Quick test of API connectivity."""
    print("Testing NamUs API")
    
    # Test search
    result = search_cases(session, take=5, skip=0)
    count = result.get("count", 0)
    cases = result.get("results", [])
    
    print(f"✅ Search API working. Total cases: {count}")
    
    if cases:
        # Test case details
        case_id = cases[0].get("id")
        if case_id:
            details = get_case_details(session, case_id)
            if details:
                print(f"✅ Case Detail API working. Sample: {details.get('namus2Number', 'N/A')}")
                return True
    
    return False


def main():
    parser = argparse.ArgumentParser(description="Scrape NamUs Unidentified Persons database")
    parser.add_argument("--test", action="store_true", help="Test API connectivity only")
    parser.add_argument("--summary-only", action="store_true", help="Only fetch case summaries, not full details")
    parser.add_argument("--by-state", action="store_true", default=True, help="Query by state to bypass 10K limit")
    parser.add_argument("--no-state-chunking", action="store_true", help="Disable state chunking (may miss cases)")
    parser.add_argument("--output", default=OUTPUT_FILE, help="Output JSON file path")
    args = parser.parse_args()
    
    print("=" * 60)
    print("NamUs Unidentified Persons Scraper")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    session = requests.Session()
    
    if args.test:
        test_api(session)
        return
    
    # Collect case summaries
    by_state = not args.no_state_chunking
    case_summaries = collect_all_case_ids(session, by_state=by_state)
    print(f"\nCollected {len(case_summaries)} case summaries.")
    
    # Save summaries
    summary_file = args.output.replace('.json', '_summaries.json')
    with open(summary_file, 'w') as f:
        json.dump(case_summaries, f, indent=2)
    print(f"Saved summaries to {summary_file}")
    
    if args.summary_only:
        print("Done (summary only mode).")
        return
    
    # Fetch full details
    print("\nFetching full case details")
    jsonl_file = args.output.replace('.json', '.jsonl')
    fetched = fetch_case_details_batch(session, case_summaries, jsonl_file)
    print(f"Fetched {fetched} new case details.")
    
    # Convert to JSON
    count = convert_jsonl_to_json(jsonl_file, args.output)
    print(f"Saved {count} records to {args.output}")


if __name__ == "__main__":
    main()
