"""
Scrapers Module - Data source scrapers for BC cold case data.

This module handles:
- BC Coroners Service GIS scraping
- Canada's Missing (NCMPUR) data collection
- BC Open Data API integration
- CanLII legal document scraping
"""

from .bccs import BCCSClient
from .ncmpur import NCMPURClient
from .canlii import CanLIIClient

__all__ = [
    "BCCSClient",
    "NCMPURClient", 
    "CanLIIClient",
]
