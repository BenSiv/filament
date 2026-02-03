import requests
from bs4 import BeautifulSoup
import json

URL = "https://charleyproject.org/case/john-andrew-aarlie"

def test_scrape():
    print(f"Fetching {URL}...")
    resp = requests.get(URL)
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    images = []
    for img in soup.find_all('img'):
        src = img.get('src', '')
        print(f"Found img src: {src}")
        if 'uploads' in src:
            if src.startswith('/'):
                 src = 'https://charleyproject.org' + src
            images.append(src)
            
    print(f"Extracted images: {images}")

if __name__ == "__main__":
    test_scrape()
