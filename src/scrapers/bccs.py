"""
BC Coroners Service - Unidentified Human Remains Viewer Client.
"""

from dataclasses import dataclass
from datetime import date
from typing import Iterator

import requests


@dataclass
class UnidentifiedCase:
    """Data from BC Coroners Service."""
    
    case_number: str
    discovery_date: date | None
    latitude: float | None
    longitude: float | None
    
    # Bio-metadata flags
    dna_available: bool = False
    dental_available: bool = False
    
    # Estimates
    estimated_age_range: str | None = None
    estimated_sex: str | None = None
    
    # Raw description
    description: str | None = None


class BCCSClient:
    """
    Client for BC Coroners Service Unidentified Human Remains data.
    
    Usage:
        client = BCCSClient()
        for case in client.fetch_all():
            print(case.case_number)
    """
    
    # ArcGIS REST API endpoint (example - actual URL needs verification)
    BASE_URL = "https://governmentofbc.maps.arcgis.com/arcgis/rest/services"
    
    def __init__(self, api_key: str | None = None):
        """
        Initialize the BCCS client.
        
        Args:
            api_key: Optional API key if required.
        """
        self.api_key = api_key
        self.session = requests.Session()
    
    def fetch_all(self) -> Iterator[UnidentifiedCase]:
        """
        Fetch all unidentified remains cases from BCCS.
        
        Yields:
            UnidentifiedCase objects.
        """
        # TODO: Implement actual ArcGIS REST API calls
        # This is a placeholder for the actual implementation
        # 
        # The real implementation would:
        # 1. Query the ArcGIS feature layer
        # 2. Parse the JSON response
        # 3. Yield UnidentifiedCase objects
        
        raise NotImplementedError(
            "BCCS scraping not yet implemented. "
            "See docs/data_sources.md for API details."
        )
    
    def fetch_by_region(self, region: str) -> Iterator[UnidentifiedCase]:
        """
        Fetch cases filtered by BC region.
        
        Args:
            region: Region name (e.g., "Lower Mainland", "Vancouver Island").
            
        Yields:
            UnidentifiedCase objects in the specified region.
        """
        raise NotImplementedError("Region filtering not yet implemented")
