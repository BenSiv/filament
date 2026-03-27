import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random
import sys

def fetch_websleuths_html(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Error fetching {url}. Code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Connection error on {url}: {e}")
        return None

def parse_websleuths_threads(html_content, source_name):
    """Parse a XenForo forum forum-page list of threads."""
    soup = BeautifulSoup(html_content, 'html.parser')
    threads = []
    
    # In XenForo 2, threads are typically in div elements under class 'structItem structItem--thread'
    thread_items = soup.find_all('div', class_=lambda c: c and 'structItem--thread' in c)
    
    for item in thread_items:
        title_tag = item.find('div', class_='structItem-title')
        if not title_tag:
            continue
        
        a_tag = title_tag.find('a', href=True, attrs={'data-tp-primary': 'on'})
        if not a_tag:
            a_tag = title_tag.find('a', href=True)

        if not a_tag:
            continue
            
        title = a_tag.text.strip()
        href = a_tag['href']
        thread_id = href.strip('/').split('.')[-1] if '.' in href else href
        url = f"https://www.websleuths.com{href}"
        
        author_tag = item.find('a', class_='username')
        author = author_tag.text.strip() if author_tag else "Unknown"
        
        threads.append({
            "id": thread_id,
            "title": title,
            "author": author,
            "url": url,
            "source": source_name,
            "selftext": title, # Forum views don't show full text, so we rely on title for now (can be expanded to scrape thread pages deeply)
            "score": 0
        })
        
    return threads

def scrape_websleuths_narratives(output_dir="data/raw/websleuths", pages=5):
    """
    Scrape thread titles and metadata from relevant Websleuths forums.
    Since Websleuths has bot protection, this uses basic headers to scrape thread titles.
    Future iterations can dive into specific thread payloads using `parse_websleuths_thread_page`.
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
                
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1"
    }
    
    os.makedirs(output_dir, exist_ok=True)
    all_extracted = []
    seen_ids = set()
    
    targets = [
        {"name": "Missing_Persons", "base_url": "https://www.websleuths.com/forums/forums/missing-persons-discussion.60/"}
    ]
    
    for target in targets:
        print(f"Scraping [{target['name']}]...")
        for page in range(1, pages + 1):
            page_url = f"{target['base_url']}page-{page}" if page > 1 else target['base_url']
            print(f"  -> Page {page}: {page_url}")
            
            html = fetch_websleuths_html(page_url, headers)
            if not html:
                break
                
            threads = parse_websleuths_threads(html, target['name'])
            if not threads:
                print("     No threads found or possible block hit.")
                break
                
            extracted_count = 0
            for thread in threads:
                if thread["id"] not in seen_ids:
                    seen_ids.add(thread["id"])
                    all_extracted.append(thread)
                    extracted_count += 1
                    
            print(f"     Extracted {extracted_count} new thread stubs.")
            delay = random.uniform(4.0, 8.0)
            print(f"     Waiting {delay:.1f}s to avoid rate limiting...")
            time.sleep(delay)
            
    output_file = os.path.join(output_dir, "websleuths_narratives.json")
    write_json(output_file, all_extracted)
    print(f"Successfully compiled {len(all_extracted)} Websleuths threads. Saved to {output_file}")
    
if __name__ == "__main__":
    scrape_websleuths_narratives()
