"""
Canada's Missing (NCMPUR) Client.
"""

from dataclasses import dataclass
from datetime import date
from typing import Iterator

import requests


@dataclass
class MissingPerson:
    """Data from Canada's Missing database."""
    
    file_number: str
    name: str | None
    
    last_seen_date: date | None
    last_seen_location: str | None
    last_seen_latitude: float | None
    last_seen_longitude: float | None
    
    # Physical description
    height_cm: int | None = None
    weight_kg: int | None = None
    eye_color: str | None = None
    hair_color: str | None = None
    
    # Distinguishing features
    distinguishing_features: list[str] | None = None
    
    # Raw description
    description: str | None = None


class NCMPURClient:
    """
    Client for Canada's Missing (NCMPUR) database.
    
    Usage:
        client = NCMPURClient()
        for person in client.fetch_bc_missing():
            print(person.file_number)
    """
    
    BASE_URL = "https://www.canadasmissing.ca"
    
    def __init__(self):
        """Initialize the NCMPUR client."""
        self.session = requests.Session()
    
    def fetch_bc_missing(self) -> Iterator[MissingPerson]:
        """
        Fetch all BC missing persons from NCMPUR.
        
        Yields:
            MissingPerson objects for British Columbia.
        """
        # TODO: Implement actual scraping
        # This requires parsing the NCMPUR website or API
        # 
        # The real implementation would:
        # 1. Search/filter for British Columbia
        # 2. Parse individual case pages
        # 3. Extract structured data
        # 4. Yield MissingPerson objects
        
        raise NotImplementedError(
            "NCMPUR scraping not yet implemented. "
            "See docs/data_sources.md for details."
        )
    
    def fetch_by_date_range(
        self,
        start_date: date,
        end_date: date
    ) -> Iterator[MissingPerson]:
        """
        Fetch BC missing persons within a date range.
        
        Args:
            start_date: Start of date range.
            end_date: End of date range.
            
        Yields:
            MissingPerson objects within the date range.
        """
        raise NotImplementedError("Date range filtering not yet implemented")
