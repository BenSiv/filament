import os
import sys
import json
import requests
import time
from dotenv import load_dotenv

# Load environment variables (like COURTLISTENER_API_KEY)
load_dotenv()

def fetch_courtlistener_opinions(query, jurisdiction="wa", api_key=None, limit=50):
    """
    Fetch legal opinions from CourtListener API based on search query.
    Requires an API token.
    """
    if not api_key:
        print("Error: COURTLISTENER_API_KEY not provided. Please set it in your environment or .env file.")
        print("You can get a free token from https://www.courtlistener.com/api/rest-info/")
        return []

    headers = {
        "Authorization": f"Token {api_key}"
    }

    # Endpoint for searching across opinions
    base_url = "https://www.courtlistener.com/api/rest/v3/search/"
    
    current_page = 1
    
    print(f"Querying CourtListener API for '{query}' in jurisdiction '{jurisdiction}'...")
    
    while True:
        params = {
            "q": query,
            "type": "o", # Opinions
            "jurisdiction": jurisdiction, # e.g. 'wa' for Washington State, 'ak' for Alaska
            "page": current_page
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                items = data.get("results", [])
                results.extend(items)
                print(f" -> Fetched page {current_page} ({len(items)} results)")
                
                if len(results) >= limit or not data.get("next"):
                    break
                    
                current_page += 1
                time.sleep(1) # Be polite to the API
            else:
                print(f"CourtListener API error: {response.status_code} - {response.text}")
                break
        except Exception as e:
            print(f"Connection error: {e}")
            break

    # Truncate to limit if we overshot
    return results[:limit]

def scrape_courtlistener_data(output_dir="data/raw/courtlistener"):
    """
    Scrape and serialize CourtListener legal opinions regarding missing persons
    and unidentified remains in border states (WA, AK, ID, MT).
    """
    scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
        
    try:
        from scraper_utils import write_json
    except ImportError:
        def write_json(path, data):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

    api_key = os.getenv("COURTLISTENER_API_KEY")
    os.makedirs(output_dir, exist_ok=True)
    
    # Target jurisdictions bordering BC or relevant for Canadian cross-border
    jurisdictions = ["wa", "ak"]
    queries = ["missing person", "unidentified remains", "coroner inquest"]
    
    all_extracted = []
    seen_ids = set()

    for jurisdiction in jurisdictions:
        for query in queries:
            opinions = fetch_courtlistener_opinions(query, jurisdiction, api_key, limit=20)
            
            extracted_count = 0
            for op in opinions:
                op_id = op.get("id")
                if op_id and op_id not in seen_ids:
                    seen_ids.add(op_id)
                    
                    # Normalize schema heavily to match Filament expectations
                    all_extracted.append({
                        "id": f"CL_{op_id}",
                        "title": op.get("caseName"),
                        "author": op.get("court"), # Utilizing court as author proxy
                        "url": f"https://www.courtlistener.com{op.get('absolute_url', '')}",
                        "source": "CourtListener",
                        "selftext": op.get("snippet", ""), # Search snippet representing the matching text
                        "date_filed": op.get("dateFiled"),
                        "jurisdiction": jurisdiction,
                        "score": 0
                    })
                    extracted_count += 1
                    
            print(f"Extracted {extracted_count} unique opinions for '{query}' in {jurisdiction.upper()}.")

    if not all_extracted:
        print("No documents extracted (API key may be missing or invalid).")
        return

    output_file = os.path.join(output_dir, "courtlistener_opinions.json")
    write_json(output_file, all_extracted)
    print(f"Successfully compiled {len(all_extracted)} CourtListener documents. Saved to {output_file}")


if __name__ == "__main__":
    scrape_courtlistener_data()
