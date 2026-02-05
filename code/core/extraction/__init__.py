"""
Extraction Module - Structured data extraction from unstructured sources.

This module handles:
- PDF document parsing (via Unstract)
- Entity extraction using LLMs
- Schema mapping to unified data model
"""

from .pipeline import ExtractionPipeline
from .entities import (
    Person,
    Location,
    PhysicalFeature,
    Clothing,
    BioEvidence,
)

__all__ = [
    "ExtractionPipeline",
    "Person",
    "Location", 
    "PhysicalFeature",
    "Clothing",
    "BioEvidence",
]
