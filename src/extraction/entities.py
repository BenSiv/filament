"""
Entity definitions for structured extraction.

These dataclasses represent the unified schema for all extracted entities.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Location:
    """Geographic location with optional precision indicator."""
    
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    region: Optional[str] = None
    precision: str = "approximate"  # exact, approximate, region-only
    description: Optional[str] = None


@dataclass
class PhysicalFeature:
    """Physical characteristic or medical condition."""
    
    category: str  # dental, skeletal, skin, other
    description: str
    medical_term: Optional[str] = None
    confidence: float = 1.0


@dataclass
class Clothing:
    """Clothing item found or described."""
    
    item_type: str  # shirt, pants, shoes, jacket, etc.
    color: Optional[str] = None
    brand: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    description: Optional[str] = None


@dataclass
class BioEvidence:
    """Biological evidence metadata (not raw data)."""
    
    evidence_type: str  # dna, dental, isotope, toxicology
    available: bool = False
    details: Optional[str] = None
    
    # DNA-specific
    dna_type: Optional[str] = None  # nuclear, mtDNA
    haplogroup: Optional[str] = None
    
    # Isotope-specific  
    isotope_region: Optional[str] = None


@dataclass
class Person:
    """
    Unified person entity for both unidentified remains and missing persons.
    """
    
    id: UUID = field(default_factory=uuid4)
    case_number: str = ""
    source: str = ""  # BCCS, NCMPUR, etc.
    person_type: str = ""  # unidentified, missing
    
    # Dates
    discovery_date: Optional[date] = None
    last_seen_date: Optional[date] = None
    
    # Location
    location: Optional[Location] = None
    
    # Physical description
    estimated_age_min: Optional[int] = None
    estimated_age_max: Optional[int] = None
    estimated_sex: Optional[str] = None
    height_cm_min: Optional[int] = None
    height_cm_max: Optional[int] = None
    weight_kg_min: Optional[int] = None
    weight_kg_max: Optional[int] = None
    
    # Related entities
    physical_features: list[PhysicalFeature] = field(default_factory=list)
    clothing: list[Clothing] = field(default_factory=list)
    bio_evidence: list[BioEvidence] = field(default_factory=list)
    
    # Narrative
    description: Optional[str] = None
    
    # Embedding (populated later)
    embedding: Optional[list[float]] = None
