#!/usr/bin/env python3
"""
Doe Network Unidentified Persons Scraper

Scrapes the Doe Network database for unidentified human remains cases.
The site uses simple HTML pages organized by geographic region.

Index pages:
  - https://www.doenetwork.org/cases/software/uid-geo-us-males.html
  - https://www.doenetwork.org/cases/software/uid-geo-us-females.html
  - https://www.doenetwork.org/cases/software/uid-geo-canada-males.html
  - https://www.doenetwork.org/cases/software/uid-geo-canada-females.html

Case pages:
  - https://www.doenetwork.org/cases/software/main.html?id={case_id}
"""

import json
import time
import argparse
import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://www.doenetwork.org"
OUTPUT_FILE = "data/raw/doenetwork_unidentified.json"
OUTPUT_JSONL = "data/raw/doenetwork_unidentified.jsonl"

# Geographic index pages
INDEX_PAGES = {
    "us_males": f"{BASE_URL}/cases/software/uid-geo-us-males.html",
    "us_females": f"{BASE_URL}/cases/software/uid-geo-us-females.html",
    "canada_males": f"{BASE_URL}/cases/software/uid-geo-canada-males.html",
    "canada_females": f"{BASE_URL}/cases/software/uid-geo-canada-females.html",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def get_case_ids_from_index(session, index_url):
    """
    Extract case IDs from a geographic index page.
    
    Args:
        session: requests.Session object
        index_url: URL of the index page
    
    Returns:
        list of case ID strings (e.g., "1579UMFL")
    """
    case_ids = []
    
    try:
        resp = session.get(index_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Find all links that contain case IDs
        # Pattern: main.html?id=XXXUMXX or similar
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'main.html?id=' in href:
                # Extract ID from query string
                match = re.search(r'id=([A-Za-z0-9]+)', href)
                if match:
                    case_ids.append(match.group(1))
        
    except requests.RequestException as e:
        print(f"Error fetching index {index_url}: {e}")
    
    return list(set(case_ids))  # Dedupe


def get_all_case_ids(session):
    """
    Collect all case IDs from all index pages.
    
    Returns:
        dict mapping case_id to metadata
    """
    all_cases = {}
    
    for category, url in INDEX_PAGES.items():
        print(f"Fetching {category} index...")
        ids = get_case_ids_from_index(session, url)
        
        for case_id in ids:
            all_cases[case_id] = {"category": category}
        
        print(f"  -> {len(ids)} cases")
        time.sleep(1)  # Be polite
    
    return all_cases


def parse_case_page(html_content, case_id):
    """
    Parse a case detail page and extract structured data.
    
    Args:
        html_content: Raw HTML content
        case_id: The case ID for reference
    
    Returns:
        dict with case data
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {"case_id": case_id, "source": "DoeNetwork"}
    
    # Try to find the case content - it's loaded in an iframe or main content
    # The actual structure varies, so we'll be flexible
    
    # Extract text from definition lists and tables
    for dl in soup.find_all(['dl', 'table']):
        # Definition lists
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        for dt, dd in zip(dts, dds):
            key = dt.get_text(strip=True).lower().replace(':', '').replace(' ', '_')
            value = dd.get_text(strip=True)
            if key and value:
                data[key] = value
        
        # Tables with header cells
        for row in dl.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True).lower().replace(':', '').replace(' ', '_')
                value = cells[1].get_text(strip=True)
                if key and value:
                    data[key] = value
    
    # Look for specific labeled spans/divs (common pattern)
    for label in soup.find_all(['strong', 'b', 'label']):
        text = label.get_text(strip=True).lower()
        if ':' in text:
            key = text.replace(':', '').replace(' ', '_')
            # Get the next sibling text
            next_text = label.find_next_sibling(string=True)
            if next_text:
                value = next_text.strip()
                if value:
                    data[key] = value
    
    # Extract any NamUs or NCIC references from the full text
    full_text = soup.get_text()
    
    namus_match = re.search(r'NamUs[:\s#]*([A-Z]*\d+)', full_text, re.IGNORECASE)
    if namus_match:
        data['namus_id'] = namus_match.group(1)
    
    ncic_match = re.search(r'NCIC[:\s#]*([A-Z0-9]+)', full_text, re.IGNORECASE)
    if ncic_match:
        data['ncic_number'] = ncic_match.group(1)
    
    # Store raw text for backup/NLP processing
    data['raw_text'] = full_text[:5000]  # Limit size
    
    return data


def scrape_case(session, case_id):
    """
    Fetch and parse a single case.
    
    Args:
        session: requests.Session
        case_id: Case ID string
    
    Returns:
        dict with case data or None on error
    """
    url = f"{BASE_URL}/cases/software/main.html?id={case_id}"
    
    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = parse_case_page(resp.content, case_id)
            data['url'] = url
            return data
        else:
            print(f"Failed to fetch {case_id}: {resp.status_code}")
    except requests.RequestException as e:
        print(f"Error fetching {case_id}: {e}")
    
    return None


def scrape_cases_batch(session, case_ids, output_file, resume=True):
    """
    Scrape multiple cases and save incrementally.
    
    Args:
        session: requests.Session
        case_ids: dict of case_id -> metadata
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
                    if 'case_id' in rec:
                        processed_ids.add(rec['case_id'])
                except json.JSONDecodeError:
                    pass
        print(f"Resuming... {len(processed_ids)} cases already processed.")
    
    total = len(case_ids)
    scraped = 0
    
    with open(output_file, 'a') as f:
        for i, (case_id, meta) in enumerate(case_ids.items()):
            if case_id in processed_ids:
                continue
            
            data = scrape_case(session, case_id)
            
            if data:
                # Merge in metadata
                data.update(meta)
                f.write(json.dumps(data) + "\n")
                f.flush()
                scraped += 1
            
            if (i + 1) % 20 == 0:
                print(f"Progress: {i+1}/{total} ({scraped} scraped)")
            
            time.sleep(1.5)  # Respectful delay
    
    return scraped


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


def test_scraper(session):
    """Quick test of scraper functionality."""
    print("Testing Doe Network scraper...")
    
    # Test index fetch
    test_url = INDEX_PAGES["us_males"]
    ids = get_case_ids_from_index(session, test_url)
    print(f"✅ Index fetch working. Found {len(ids)} case IDs.")
    
    if ids:
        # Test case scrape
        test_id = ids[0]
        data = scrape_case(session, test_id)
        if data:
            print(f"✅ Case scrape working. Sample case: {test_id}")
            return True
    
    return False


def main():
    parser = argparse.ArgumentParser(description="Scrape Doe Network Unidentified Persons database")
    parser.add_argument("--test", action="store_true", help="Test scraper only")
    parser.add_argument("--index-only", action="store_true", help="Only fetch case IDs, not details")
    parser.add_argument("--output", default=OUTPUT_FILE, help="Output JSON file path")
    parser.add_argument("--categories", nargs="+", choices=list(INDEX_PAGES.keys()),
                        help="Specific categories to scrape")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Doe Network Unidentified Persons Scraper")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    session = requests.Session()
    
    if args.test:
        test_scraper(session)
        return
    
    # Collect case IDs
    if args.categories:
        # Filter to specific categories
        filtered = {k: v for k, v in INDEX_PAGES.items() if k in args.categories}
        original = INDEX_PAGES.copy()
        INDEX_PAGES.clear()
        INDEX_PAGES.update(filtered)
    
    case_ids = get_all_case_ids(session)
    print(f"\nCollected {len(case_ids)} unique case IDs.")
    
    # Save case IDs
    ids_file = args.output.replace('.json', '_ids.json')
    with open(ids_file, 'w') as f:
        json.dump(case_ids, f, indent=2)
    print(f"Saved case IDs to {ids_file}")
    
    if args.index_only:
        print("Done (index only mode).")
        return
    
    # Scrape case details
    print("\nScraping case details...")
    jsonl_file = args.output.replace('.json', '.jsonl')
    scraped = scrape_cases_batch(session, case_ids, jsonl_file)
    print(f"Scraped {scraped} new cases.")
    
    # Convert to JSON
    count = convert_jsonl_to_json(jsonl_file, args.output)
    print(f"Saved {count} records to {args.output}")


if __name__ == "__main__":
    main()
