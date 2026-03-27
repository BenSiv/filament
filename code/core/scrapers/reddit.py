import requests
import json
import os
import time

def fetch_reddit_json(url, headers):
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching {url}. Code: {response.status_code}")
        return []
    try:
        data = response.json()
        return data.get("data", {}).get("children", [])
    except json.JSONDecodeError:
        print("Error: Received non-JSON response")
        return []

def scrape_reddit_narratives(output_dir="data/raw/reddit", limit=100):
    headers = {"User-Agent": "Filament/1.0 (Research tool for cold case narrative extraction)"}
    os.makedirs(output_dir, exist_ok=True)
    
    # Targets focusing strictly on Missing Persons and Unidentified Remains
    targets = [
        {"name": "gratefuldoe", "url": f"https://www.reddit.com/r/gratefuldoe/top.json?t=all&limit={limit}"},
        {"name": "MissingPersons", "url": f"https://www.reddit.com/r/MissingPersons/top.json?t=all&limit={limit}"},
        {"name": "WithoutATrace", "url": f"https://www.reddit.com/r/WithoutATrace/top.json?t=all&limit={limit}"},
        {"name": "UM_Disappearances", "url": f"https://www.reddit.com/r/UnresolvedMysteries/search.json?q=flair_name:\"Unexplained Disappearance\"&restrict_sr=1&sort=top&limit={limit}"},
        {"name": "UM_Unidentified", "url": f"https://www.reddit.com/r/UnresolvedMysteries/search.json?q=flair_name:\"Unidentified Remains\"&restrict_sr=1&sort=top&limit={limit}"}
    ]
    
    all_extracted = []
    seen_ids = set()
    seen_urls = set()
    
    for target in targets:
        print(f"Scraping [{target['name']}]...")
        posts = fetch_reddit_json(target["url"], headers)
        
        extracted_count = 0
        for post in posts:
            p_data = post["data"]
            # We only care about text posts with a substantial narrative
            if p_data.get("selftext") and len(p_data.get("selftext", "")) > 100:
                post_id = p_data.get("id")
                post_url = p_data.get("url")
                if post_id and post_id in seen_ids:
                    continue
                if post_url and post_url in seen_urls:
                    continue
                if post_id:
                    seen_ids.add(post_id)
                if post_url:
                    seen_urls.add(post_url)
                all_extracted.append({
                    "id": p_data.get("id"),
                    "title": p_data.get("title"),
                    "author": p_data.get("author"),
                    "created_utc": p_data.get("created_utc"),
                    "url": p_data.get("url"),
                    "source": target["name"],
                    "selftext": p_data.get("selftext"),
                    "score": p_data.get("score")
                })
                extracted_count += 1
                
        print(f"  -> Extracted {extracted_count} narrative posts.")
        time.sleep(2) # Respect rate limits slightly
        
    output_file = os.path.join(output_dir, "missing_and_uhr_narratives.json")
    with open(output_file, "w") as f:
        json.dump(all_extracted, f, indent=2)
        
    print(f"Successfully compiled {len(all_extracted)} total Missing/UHR narrative posts. Saved to {output_file}")

if __name__ == "__main__":
    scrape_reddit_narratives()
