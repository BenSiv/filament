"""
Ingest podcast transcripts from Podscribe.
"""

import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from core.scrapers.podscribe_scraper import PodscribeClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Target Series
SERIES = {
    "The Vanished Podcast": "870", # Series ID
    # Add more as needed
}

DATA_DIR = Path("data/raw/podcasts_podscribe")

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def ingest_podcasts(limit: int = 5):
    """
    Fetch and save transcripts for configuring series.
    """
    ensure_dir(DATA_DIR)
    
    client = PodscribeClient()
    
    for series_name, series_id in SERIES.items():
        logger.info(f"Starting ingestion for: {series_name} (Series {series_id})")
        
        try:
            transcripts = client.fetch_series_transcripts(series_id=series_id, limit=limit)
            
            count = 0
            for transcript in transcripts:
                # Create filename: series_name_videoid.json
                safe_name = series_name.lower().replace(" ", "_")
                # video_id in podscribe scraper is url-based, safe enough?
                # usually just the number part would be better but let's see.
                
                filename = f"{safe_name}_{transcript.video_id}.json"
                file_path = DATA_DIR / filename
                
                # Enrich with generic data if scraper missed it
                if not transcript.channel_name or transcript.channel_name == "Podscribe Series":
                     transcript.channel_name = series_name
                
                logger.info(f"Saving transcript: {transcript.title} ({transcript.video_id})")
                
                # Save to JSON
                with open(file_path, "w", encoding="utf-8") as f:
                    data = asdict(transcript)
                    data['id'] = str(data['id'])
                    if data.get('published_at'):
                         data['published_at'] = data['published_at'].isoformat()
                         
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                count += 1
            
            logger.info(f"Completed {series_name}: {count} transcripts saved.")
            
        except Exception as e:
            logger.error(f"Failed to ingest series {series_name}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest podcast transcripts from Podscribe")
    parser.add_argument("--limit", type=int, default=3, help="Number of episodes per series to fetch")
    args = parser.parse_args()
    
    ingest_podcasts(limit=args.limit)
