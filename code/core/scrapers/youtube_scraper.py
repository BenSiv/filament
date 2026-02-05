"""
YouTube Podcast Scraper.
"""

from datetime import datetime
from typing import Iterator

import logging
import scrapetube
from youtube_transcript_api import YouTubeTranscriptApi

from core.extraction.podcasts import PodcastTranscript

logger = logging.getLogger(__name__)



class YouTubePodcastClient:
    """
    Client for fetching podcast transcripts from YouTube channels.
    """
    
    def __init__(self):
        """Initialize the YouTube Podcast client."""
        # youtube_transcript_api doesn't store state, but we might want to config proxies here later
        pass
    
    def fetch_channel_transcripts(self, channel_id: str = None, channel_url: str = None, limit: int = 10) -> Iterator[PodcastTranscript]:
        """
        Fetch transcripts for the most recent videos in a channel.
        
        Args:
            channel_id: The YouTube channel ID (e.g., 'UC...')
            channel_url: The YouTube channel URL (e.g. 'https://youtube.com/@...')
            limit: Maximum number of videos to process.
            
        Yields:
            PodcastTranscript objects.
        """
        # Fetch video list
        if channel_url:
            videos = scrapetube.get_channel(channel_url=channel_url, limit=limit)
        else:
            videos = scrapetube.get_channel(channel_id=channel_id, limit=limit)
        
        videos_list = list(videos) 
        logger.info(f"Found {len(videos_list)} videos for {channel_id or channel_url}")
        
        for video in videos_list:
            video_id = video['videoId']
            title = video.get('title', {}).get('runs', [{}])[0].get('text', 'Unknown Title')
            
            transcript_text, segments = self._get_transcript(video_id)
            
            if transcript_text:
                yield PodcastTranscript(
                    video_id=video_id,
                    channel_id=channel_id,
                    channel_name="Unknown Channel", 
                    title=title,
                    text=transcript_text,
                    segments=segments
                )
            else:
                logger.warning(f"No transcript for {video_id}: {title}")
    
    def _get_transcript(self, video_id: str) -> tuple[str, list[dict]]:
        """
        Attempt to fetch transcript text and segments.
        
        Returns:
            (full_text, segments_list)
        """
        try:
            # Instantiate per our verification findings
            api = YouTubeTranscriptApi()
            
            # Try list_transcripts to find English manually if auto-fetch fails?
            # Or just use list_transcripts pattern which is robust
            # Verified: this version uses .list()
            transcript_list = api.list(video_id)
            
            # Find generated or manual English transcript
            # Prefer manual, fall back to generated
            try:
                # Manual English - assuming TranscriptList object signature matches
                transcript_obj = transcript_list.find_manually_created_transcript(['en'])
            except:
                try:
                    # Auto-generated English
                    transcript_obj = transcript_list.find_generated_transcript(['en'])
                except:
                     # Any English?
                     return "", []

            segments = transcript_obj.fetch()
            
            # Combine text
            # Version 1.2.3 returns objects with .text attribute
            # But let's check if it's dict or object to be safe? 
            # The error 'not subscriptable' confirms it's an object.
            full_text = " ".join([seg.text for seg in segments])
            
            # Convert segments to dicts for storage if needed, or keep as is if compatible
            # Our PodcastTranscript model expects 'segments': list[dict]
            segments_dicts = [
                {'text': seg.text, 'start': seg.start, 'duration': seg.duration}
                for seg in segments
            ]
            
            return full_text, segments_dicts
            
        except Exception as e:
            logger.debug(f"Failed to get transcript for {video_id}: {e}")
            return "", []
