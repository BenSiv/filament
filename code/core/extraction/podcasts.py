"""
Podcast entity definitions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

@dataclass
class PodcastTranscript:
    """
    Represents a single podcast episode transcript.
    """
    id: UUID = field(default_factory=uuid4)
    video_id: str = ""
    channel_name: str = ""
    channel_id: str = ""
    title: str = ""
    published_at: Optional[datetime] = None
    
    # The full text content
    text: str = ""
    
    # Raw transcript segments (optional, for timestamp lookup)
    # List of dicts: [{'text': '...', 'start': 0.0, 'duration': 1.0}]
    segments: list[dict] = field(default_factory=list)
    
    source_url: str = ""
    
    def __post_init__(self):
        if not self.source_url and self.video_id:
            self.source_url = f"https://www.youtube.com/watch?v={self.video_id}"
