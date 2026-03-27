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
from .websleuths import scrape_websleuths_narratives
from .courtlistener import scrape_courtlistener_data

__all__ = [
    "BCCSClient",
    "NCMPURClient", 
    "CanLIIClient",
    "scrape_websleuths_narratives",
    "scrape_courtlistener_data",
]
