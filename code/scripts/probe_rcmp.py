
import requests
from bs4 import BeautifulSoup

base_url = "https://www.services.rcmp-grc.gc.ca/missing-disparus/results-resultats.jsf"

# Test 1: ?first=60 (0-based index for page 2)
url_first = f"{base_url}?first=60"
print(f"Testing {url_first}...")
resp = requests.get(url_first)
soup = BeautifulSoup(resp.content, 'html.parser')
links_first = soup.find_all('a', href=lambda h: h and 'case-dossier.jsf' in h)
print(f"  Found {len(links_first)} cases")
if links_first:
    first_case_text = links_first[1].text.strip() if len(links_first) > 1 else "" # Index 1 because often first is empty/image
    print(f"  First case on page: {first_case_text}")

# Test 2: ?page=2
url_page = f"{base_url}?page=2"
print(f"\nTesting {url_page}...")
resp = requests.get(url_page)
soup = BeautifulSoup(resp.content, 'html.parser')
links_page = soup.find_all('a', href=lambda h: h and 'case-dossier.jsf' in h)
print(f"  Found {len(links_page)} cases")
if links_page:
    first_case_text_page = links_page[1].text.strip() if len(links_page) > 1 else ""
    print(f"  First case on page: {first_case_text_page}")

# Check for selenium drivers
import shutil
print("\nChecking for browsers/drivers:")
print(f"  google-chrome: {shutil.which('google-chrome')}")
print(f"  chromium: {shutil.which('chromium')}")
print(f"  firefox: {shutil.which('firefox')}")
print(f"  chromedriver: {shutil.which('chromedriver')}")
print(f"  geckodriver: {shutil.which('geckodriver')}")
