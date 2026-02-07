#!/usr/bin/env python3
"""
Doe Network Unidentified Persons Scraper (Selenium Version)

Scrapes the Doe Network database for unidentified human remains cases.
Uses Selenium to bypass simple bot protection/403 errors.
"""

import json
import time
import argparse
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Configuration
BASE_URL = "https://www.doenetwork.org"
OUTPUT_FILE = "data/raw/doenetwork_unidentified.json"

# Geographic index pages
INDEX_PAGES = {
    "us_males": f"{BASE_URL}/cases/software/uid-geo-us-males.html",
    "us_females": f"{BASE_URL}/cases/software/uid-geo-us-females.html",
    "canada_males": f"{BASE_URL}/cases/software/uid-geo-canada-males.html",
    "canada_females": f"{BASE_URL}/cases/software/uid-geo-canada-females.html",
}

def init_driver():
    """Initialize Headless Chrome Driver."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

def get_case_ids_from_index(driver, index_url):
    """Extract case IDs from index page using Selenium."""
    case_ids = []
    try:
        print(f"Navigating to {index_url}")
        driver.get(index_url)
        time.sleep(3) # Wait for JS/Render
        
        # Use BS4 for faster parsing of the source
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'main.html?id=' in href:
                match = re.search(r'id=([A-Za-z0-9]+)', href)
                if match:
                    case_ids.append(match.group(1))
                    
    except Exception as e:
        print(f"Error fetching index {index_url}: {e}")
    
    return list(set(case_ids))

def get_all_case_ids(driver):
    """Collect all case IDs from all index pages."""
    all_cases = {}
    for category, url in INDEX_PAGES.items():
        print(f"Fetching {category} index")
        ids = get_case_ids_from_index(driver, url)
        for case_id in ids:
            all_cases[case_id] = {"category": category}
        print(f"  -> {len(ids)} cases")
    return all_cases

def parse_case_page(html_content, case_id):
    """Parse case detail page (BS4 logic preserved)."""
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {"case_id": case_id, "source": "DoeNetwork"}
    
    # Extract text from definition lists and tables
    for dl in soup.find_all(['dl', 'table']):
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        for dt, dd in zip(dts, dds):
            key = dt.get_text(strip=True).lower().replace(':', '').replace(' ', '_')
            value = dd.get_text(strip=True)
            if key and value:
                data[key] = value
        
        for row in dl.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True).lower().replace(':', '').replace(' ', '_')
                value = cells[1].get_text(strip=True)
                if key and value:
                    data[key] = value
    
    # Text-based extraction
    for label in soup.find_all(['strong', 'b', 'label']):
        text = label.get_text(strip=True).lower()
        if ':' in text:
            key = text.replace(':', '').replace(' ', '_')
            next_text = label.find_next_sibling(string=True)
            if next_text:
                value = next_text.strip()
                if value:
                    data[key] = value
    
    full_text = soup.get_text()
    
    # Expanded NamUs Pattern Matching
    # NamUs UP # 12345, NamUs # 12345, NamUs Case Number: 12345
    namus_match = re.search(r'NamUs\s*(?:UP)?\s*(?:#|Case|Number|:)*\s*([0-9]+)', full_text, re.IGNORECASE)
    if namus_match:
        data['namus_id'] = namus_match.group(1)
    
    ncic_match = re.search(r'NCIC[:\s#]*([A-Z0-9]+)', full_text, re.IGNORECASE)
    if ncic_match:
        data['ncic_number'] = ncic_match.group(1)
        
    # Narrative Extraction (Case Circumstances)
    # Usually under a header "Circumstances of Discovery" or similar
    # We'll just grab everything for now or look for specific h3/h4
    
    data['raw_text'] = full_text[:10000]
    return data

def scrape_case(driver, case_id):
    """Fetch and parse a single case using Selenium."""
    url = f"{BASE_URL}/cases/software/main.html?id={case_id}"
    try:
        driver.get(url)
        # Check for 404/Empty?
        # Only meaningful check is if content loaded
        content = driver.page_source
        if "Circumstances of Discovery" in content or "Case Details" in content:
            data = parse_case_page(content, case_id)
            data['url'] = url
            return data
        else:
             # Try minor wait
             time.sleep(1)
             data = parse_case_page(driver.page_source, case_id)
             data['url'] = url
             return data
             
    except Exception as e:
        print(f"Error fetching {case_id}: {e}")
    return None

def scrape_cases_batch(driver, case_ids, output_file, resume=True):
    """Scrape multiple cases."""
    processed_ids = set()
    if resume and os.path.exists(output_file):
        with open(output_file, 'r') as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if 'case_id' in rec:
                        processed_ids.add(rec['case_id'])
                except: pass
        print(f"Resuming... {len(processed_ids)} cases known.")
    
    total = len(case_ids)
    scraped = 0
    
    with open(output_file, 'a') as f:
        for i, (case_id, meta) in enumerate(case_ids.items()):
            if case_id in processed_ids:
                continue
            
            data = scrape_case(driver, case_id)
            if data:
                data.update(meta)
                f.write(json.dumps(data) + "\n")
                f.flush()
                scraped += 1
            
            if (i + 1) % 10 == 0:
                print(f"Progress: {i+1}/{total} ({scraped} new)")
            
            time.sleep(0.5) # Selenium is slower, smaller delay needed
            
    return scraped

def convert_jsonl_to_json(jsonl_file, json_file):
    records = []
    with open(jsonl_file, 'r') as f:
        for line in f:
            try: records.append(json.loads(line))
            except: pass
    with open(json_file, 'w') as f:
        json.dump(records, f, indent=2)
    return len(records)

def main():
    parser = argparse.ArgumentParser(description="Doe Network Scraper (Selenium)")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--index-only", action="store_true")
    parser.add_argument("--output", default=OUTPUT_FILE)
    parser.add_argument("--categories", nargs="+", choices=list(INDEX_PAGES.keys()))
    args = parser.parse_args()
    
    print("Starting Selenium Scraper")
    driver = init_driver()
    
    try:
        if args.test:
            print("Running Test Mode")
            ids = get_case_ids_from_index(driver, INDEX_PAGES["us_males"])
            print(f"Found {len(ids)} IDs.")
            if ids:
                print(f"Scraping first ID: {ids[0]}")
                data = scrape_case(driver, ids[0])
                print(json.dumps(data, indent=2))
            return

        # Filters
        if args.categories:
            filtered = {k: v for k, v in INDEX_PAGES.items() if k in args.categories}
            INDEX_PAGES.clear()
            INDEX_PAGES.update(filtered)

        case_ids = get_all_case_ids(driver)
        
        if args.index_only:
            # Save IDs
            with open(args.output.replace('.json', '_ids.json'), 'w') as f:
                json.dump(case_ids, f, indent=2)
            return

        jsonl_file = args.output.replace('.json', '.jsonl')
        scrape_cases_batch(driver, case_ids, jsonl_file)
        convert_jsonl_to_json(jsonl_file, args.output)
        
    finally:
        driver.quit()
        print("Driver closed.")

if __name__ == "__main__":
    main()
