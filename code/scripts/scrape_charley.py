import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re

OUTPUT_FILE = 'data/raw/charley_washington.json'
INDEX_URL = 'https://charleyproject.org/case-searches/geographical-cases?region=Washington'

def get_case_urls():
    """Fetches case URLs from the Washington index page."""
    # Check if we have a local debug file first to save bandwidth
    if os.path.exists('data/raw/debug_charley_wa.html'):
        print("Using local index file")
        with open('data/raw/debug_charley_wa.html', 'r') as f:
            soup = BeautifulSoup(f, 'html.parser')
    else:
        print("Fetching index from web")
        resp = requests.get(INDEX_URL)
        if resp.status_code != 200:
            print(f"Failed to fetch index: {resp.status_code}")
            return []
        soup = BeautifulSoup(resp.content, 'html.parser')

    links = []
    # Find all links to cases
    # They look like https://charleyproject.org/case/name-matching-regex
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'charleyproject.org/case/' in href:
            links.append(href)
    
    # Dedup
    return list(set(links))

def parse_case(html_content, case_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {'url': case_url}
    
    # Title / Name
    title = soup.find('h1', class_='jumbotron-title') # heuristic based on common bootstrap/theme
    # Fallback if no specific class
    if not title:
        title = soup.find('h1')
    data['name'] = title.get_text(strip=True) if title else 'Unknown'
    
    # Details List
    details = {}
    # Looking for the <ul> containing <li><strong>Key</strong> Value</li>
    # We can just iterate all li tags with strong children
    for li in soup.find_all('li'):
        strong = li.find('strong')
        if strong:
            key = strong.get_text(strip=True)
            # Value is the text siblings
            # We need to be careful not to get the key text
            value = li.get_text(strip=True).replace(key, '', 1).strip()
            details[key] = value
            
    data['details'] = details
    
    # Narrative sections usually follow headers like "Details of Disappearance"
    # The structure seems to be dynamic sections.
    # Let's simple dump all text from "section" tags or similar?
    # Inspecting the debug file showed the details details list is inside a div.
    # The narrative usually is separate.
    
    # Heuristic: Find specific headers and get next siblings
    for header in soup.find_all(['h3', 'h4', 'strong']):
        text = header.get_text(strip=True)
        if 'Details of Disappearance' in text:
            # The narrative is usually the next p or div
            narrative = []
            curr = header.find_next_sibling()
            while curr and curr.name in ['p', 'div'] and 'Investigating Agency' not in curr.get_text():
                 narrative.append(curr.get_text(strip=True))
                 curr = curr.find_next_sibling()
            data['narrative'] = "\n".join(narrative)
            
    # Images
    data['images'] = []
    # Charley usually puts images in .col-sm-4 or img tags in the top section
    # Iterate all img tags, filter out logos/icons
    for img in soup.find_all('img'):
        src = img.get('src', '')
        # Filter heuristics: Charley Project uses WP uploads
        if 'uploads' in src:
             if src.startswith('/'):
                 src = 'https://charleyproject.org' + src
             data['images'].append(src)
             
    return data

def main():
    urls = get_case_urls()
    print(f"Found {len(urls)} cases.")
    
    cases = []
    # Process
    for i, url in enumerate(urls):
        print(f"[{i+1}/{len(urls)}] Scraping {url}")
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                case_data = parse_case(resp.content, url)
                if case_data:
                    cases.append(case_data)
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        
        time.sleep(1) # Be polite
        
        # Incremental save
        if i % 10 == 0:
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(cases, f, indent=2)

    # Final save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(cases, f, indent=2)
    print("Done.")

if __name__ == '__main__':
    main()
