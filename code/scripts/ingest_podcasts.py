"""
Ingest podcast transcripts from YouTube channels.
"""

import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from core.scrapers.youtube_scraper import YouTubePodcastClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Target Channels
CHANNELS = {
    "The Vanished Podcast": "https://www.youtube.com/@vanishedpodcast8746",
    "Casefile True Crime": "https://www.youtube.com/@CasefileTrueCrimePodcast",
    # Add more as needed
}

DATA_DIR = Path("data/raw/podcasts")

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def ingest_podcasts(limit: int = 10):
    """
    Fetch and save transcripts for configuring channels.
    """
    ensure_dir(DATA_DIR)
    
    client = YouTubePodcastClient()
    
    for channel_name, channel_url in CHANNELS.items():
        logger.info(f"Starting ingestion for: {channel_name}")
        
        try:
            transcripts = client.fetch_channel_transcripts(channel_url=channel_url, limit=limit)
            
            count = 0
            for transcript in transcripts:
                # Create filename: channel_name_videoid.json
                safe_name = channel_name.lower().replace(" ", "_")
                filename = f"{safe_name}_{transcript.video_id}.json"
                file_path = DATA_DIR / filename
                
                # Enrich with channel name since scraper returns generic
                transcript.channel_name = channel_name
                
                logger.info(f"Saving transcript: {transcript.title} ({transcript.video_id})")
                
                # Save to JSON
                with open(file_path, "w", encoding="utf-8") as f:
                    # Convert dataclass to dict, handle datetime serializing if needed (currently none in model)
                    data = asdict(transcript)
                    # Convert UUID to str
                    data['id'] = str(data['id'])
                    # date handling if we add it later
                    if data.get('published_at'):
                         data['published_at'] = data['published_at'].isoformat()
                         
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                count += 1
            
            logger.info(f"Completed {channel_name}: {count} transcripts saved.")
            
        except Exception as e:
            logger.error(f"Failed to ingest channel {channel_name}: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest podcast transcripts")
    parser.add_argument("--limit", type=int, default=5, help="Number of videos per channel to check")
    args = parser.parse_args()
    
    ingest_podcasts(limit=args.limit)
