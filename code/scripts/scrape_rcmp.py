
import json
import time
import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
BASE_URL = "https://www.services.rcmp-grc.gc.ca/missing-disparus"
START_URL = f"{BASE_URL}/results-resultats.jsf"
OUTPUT_FILE = "data/raw/rcmp_missing_persons.json"

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)
    return driver

def get_case_ids(driver):
    case_ids = set()
    driver.get(START_URL)
    
    # Wait for any case link to appear
    print("Waiting for results to load...")
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='case-dossier']"))
    )
    
    page_num = 1
    while True:
        print(f"Scraping page {page_num}...")
        
        # Extract links from current page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        links = soup.find_all('a', href=lambda h: h and 'case-dossier.jsf' in h)
        
        new_ids = 0
        for link in links:
            href = link.get('href')
            # href format: /missing-disparus/case-dossier.jsf?case=2014001708&id=0&lang=en
            if 'case=' in href:
                case_id = href.split('case=')[1].split('&')[0]
                if case_id not in case_ids:
                    case_ids.add(case_id)
                    new_ids += 1
        
        print(f"  Found {new_ids} new cases. Total: {len(case_ids)}")
        
        # Find Next button
        # The pagination uses JSF, look for the 'Next' link
        try:
            # Look for a link with text "Next" or title "Next" validation
            next_btn = driver.find_elements(By.XPATH, "//a[contains(text(), 'Next')]")
            if not next_btn:
                # Try finding by rel="next"
                next_btn = driver.find_elements(By.CSS_SELECTOR, "a[rel='next']")
            
            if next_btn and next_btn[0].is_enabled():
                # Check if it's not disabled (parent li class)
                parent = next_btn[0].find_element(By.XPATH, "..")
                if "disabled" in parent.get_attribute("class"):
                    print("Next button disabled. Reached end.")
                    break
                
                # Use JS click to avoid interception
                driver.execute_script("arguments[0].scrollIntoView(true);", next_btn[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", next_btn[0])
                page_num += 1
                
                if page_num > 100: # Cover all ~2700 cases (approx 60 per page means ~45 pages)
                    print("Reached page limit. Stopping ID collection.")
                    break
                
                # Wait for loading - simplest way is small sleep + check for staleness or new content
                # JSF AJAX updates are tricky to wait for perfectly
                time.sleep(2) 
            else:
                print("No Next button found.")
                break
        except Exception as e:
            print(f"Error navigating: {e}")
            break
            
    return list(case_ids)

def scrape_case_details(case_id):
    url = f"{BASE_URL}/case-dossier.jsf?case={case_id}&lang=en"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"Failed to fetch {case_id}: {resp.status_code}")
            return None
            
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        case_data = {
            "case_id": case_id,
            "url": url,
            "title": soup.title.string.strip() if soup.title else "",
            "narrative": ""
        }
        
        # Extract basic fields often found in definition lists <dl> or tables
        # The structure varies, but we'll try to grab common labels
        # Assuming typical dl-horizontal or similar
        
        # Extract all text from main content for keyword search
        main_content = soup.find(id="wb-cont")
        if main_content:
             case_data["narrative"] = main_content.get_text(" ", strip=True)
        
        # Try to parse specific fields if possible (refine later if needed)
        # Look for labels like "Location:", "Date last seen:", etc.
        # Check specific containers if analysis reveals them. 
        # For now, raw narrative is ensuring we don't miss "tourist" keywords.
        
        return case_data
        
    except Exception as e:
        print(f"Error scraping case {case_id}: {e}")
        return None

def main():
    print("Starting scraper...")
    driver = setup_driver()
    print("Collecting Case IDs...")
    case_ids = get_case_ids(driver)
    # Driver kept open for details?
    # To speed up, let's try transferring cookies to requests
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    # Copy cookies
    cookies = driver.get_cookies()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])
    
    print(f"Collected {len(case_ids)} unique Case IDs. Switching to Requests with session...")
    
    jsonl_file = OUTPUT_FILE + "l"
    
    # Save IDs just in case
    with open('data/raw/case_ids.txt', 'w') as f:
        for cid in case_ids:
            f.write(cid + "\n")
            
    # Load already processed IDs to resume (Skip existing)
    processed_ids = set()
    if os.path.exists(jsonl_file):
        with open(jsonl_file, 'r') as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if 'case_id' in rec:
                        processed_ids.add(rec['case_id'])
                except:
                    pass
    print(f"Resuming... {len(processed_ids)} cases already processed. {len(case_ids) - len(processed_ids)} remaining.")

    count = 0
    with open(jsonl_file, 'a') as f_out: # Append mode
        for cid in case_ids:
            if cid in processed_ids:
                continue
                
            url = f"{BASE_URL}/case-dossier.jsf?case={cid}&lang=en"
            try:
                # Use session
                resp = session.get(url, timeout=10)
                
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.content, 'html.parser')
                    main_tag = soup.find("main")
                    narrative = main_tag.get_text(" ", strip=True) if main_tag else ""
                    
                    # Verify we got content (not disclaimer)
                    if "Disclaimer" in soup.title.string or "Language" in soup.title.string:
                         print(f"Session might have expired or disclaimer hit for {cid}")
                         # Fallback to selenium for this one? or just skip
                    
                    details = {}
                    dls = soup.find_all("dl")
                    for dl in dls:
                        dts = dl.find_all("dt")
                        dds = dl.find_all("dd")
                        for dt, dd in zip(dts, dds):
                            key = dt.get_text(strip=True).strip(':')
                            val = dd.get_text(strip=True)
                            details[key] = val
                    
                    if details:
                         narrative += " " + json.dumps(details)
                    
                    record = {
                        "case_id": cid,
                        "url": url,
                        "title": soup.title.string.strip() if soup.title else "",
                        "narrative": narrative,
                        "details": details
                    }
                    f_out.write(json.dumps(record) + "\n")
                    f_out.flush()
                else:
                    print(f"Failed {cid}: {resp.status_code}")

            except Exception as e:
                print(f"Error {cid}: {e}")
            
            count += 1
            if count % 20 == 0:
                print(f"Processed {count}/{len(case_ids)}")
    
    driver.quit()

    # Convert JSONL to JSON
    final_data = []
    try:
        with open(jsonl_file, 'r') as f_in:
            for line in f_in:
                final_data.append(json.loads(line))
        with open(OUTPUT_FILE, 'w') as f_final:
            json.dump(final_data, f_final, indent=2)
    except FileNotFoundError:
        pass
        
    print(f"Saved {len(final_data)} records to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
