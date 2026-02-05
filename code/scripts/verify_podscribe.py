"""
Verify Podscribe Scraper.
"""
import sys
import os
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from core.scrapers.podscribe_scraper import PodscribeClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_scraper():
    # The Vanished Podcast Series ID
    SERIES_ID = "870"
    
    print(f"Initializing scraper for Series {SERIES_ID}...")
    client = PodscribeClient()
    
    print("Fetching last 3 transcripts...")
    try:
        transcripts = client.fetch_series_transcripts(series_id=SERIES_ID, limit=3)
        
        count = 0
        for t in transcripts:
            count += 1
            print(f"\n[{count}] Found Transcript!")
            print(f"Title: {t.title}")
            print(f"Source URL: {t.source_url}")
            print(f"Text Snippet: {t.text[:200]}...")
            
            if len(t.text) < 100:
                print("WARNING: Text seems too short!")
            
        if count == 0:
            print("No transcripts found.")
            
    except Exception as e:
        print(f"Scraper failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_scraper()
