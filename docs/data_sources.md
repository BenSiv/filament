# Phase 1: Data Sources

This document details the primary data sources for the BC Cold Case system - the "Hard Facts" that form the foundation of reliable investigative intelligence.

## Primary Entity Databases (British Columbia)

### 1. BC Coroners Service (BCCS) Unidentified Human Remains Viewer

**Source**: [BC Coroners Service GIS Viewer](https://governmentofbc.maps.arcgis.com/apps/webappviewer/index.html?id=ad0d2f3e4c6b4b4a8a9c0e7f0b2d4a6c)

**Data Available**:
| Field | Description | Example |
|-------|-------------|---------|
| Case Number | Unique identifier | `2019-0123-0001` |
| Discovery Date | Date remains were found | `2019-03-15` |
| Coordinates | Exact or approximate location | `49.2827° N, 123.1207° W` |
| Bio-Metadata Flags | Evidence availability | "DNA available", "Dental records available" |

**Access Methods**:
1. **GIS Layer Scraping**: Parse the public ArcGIS REST API
2. **BC Data Catalogue**: Request dataset via [data.gov.bc.ca](https://data.gov.bc.ca)

**Integration Notes**:
```python
# Example API endpoint pattern
BCCS_API = "https://governmentofbc.maps.arcgis.com/arcgis/rest/services/..."

# Key fields to extract
BCCS_FIELDS = [
    "case_number",
    "discovery_date",
    "latitude",
    "longitude",
    "dna_available",
    "dental_available",
    "estimated_age_range",
    "estimated_sex"
]
```

---

### 2. Canada's Missing (NCMPUR)

**Source**: [National Centre for Missing Persons and Unidentified Remains](https://www.canadasmissing.ca)

**Data Available**:
| Field | Description | Example |
|-------|-------------|---------|
| File Number | National unique ID | `MP-2018-BC-0456` |
| Physical Stats | Height, weight, eye/hair color | `175cm, 70kg, Blue eyes` |
| Last Seen Date | Date of disappearance | `2018-07-22` |
| Last Seen Location | Geographic area | `Hope, British Columbia` |
| Distinguishing Features | Scars, tattoos, medical conditions | `Scoliosis, appendectomy scar` |

**Filtering Strategy**:
- Filter national database for `Province = British Columbia`
- Cross-reference with Yukon/Alberta border regions

**Key Data Points for Matching**:
- Physical description (height, weight, age range)
- Clothing at time of disappearance
- Medical history and distinguishing features
- Last known location (for geographic proximity scoring)

---

### 3. BC Open Data Geospatial Layers

**Source**: [BC Data Catalogue](https://data.gov.bc.ca)

**Contextual Layers**:

| Dataset | Use Case |
|---------|----------|
| **BC Wildfire - Historical** | Explain preservation conditions, discovery timeline |
| **First Responders Facilities** | Context for discovery locations |
| **Provincial Parks Boundaries** | Remote area classification |
| **Major Road Network** | Accessibility analysis |
| **Historical Weather Data** | Decomposition rate estimation |

**Example Use Case**:
> If remains are found in a remote area, overlaying historical wildfire data can explain:
> - Why remains were exposed (fire removed vegetation)
> - Discovery timing (post-fire survey)
> - Preservation conditions (charring patterns)

**Integration Pattern**:
```python
# Layer intersection query
def get_contextual_data(lat: float, lon: float, date: datetime) -> dict:
    """
    Get contextual geospatial data for a discovery location.
    
    Returns:
        - Nearest community
        - Distance to road network
        - Wildfire history within 10km
        - Terrain classification
    """
    ...
```

---

## Legal & Bio-Metadata Text Sources

### 4. CanLII & BC Courts

**Source**: [CanLII](https://www.canlii.org)

**Data Available**:
- Court transcripts and decisions
- Inquiry documents
- Criminal case records

**Search Strategies**:
| Query Pattern | Purpose |
|---------------|---------|
| `"R. v. [Name]"` | Criminal cases with victim/suspect details |
| `"Inquiry" AND "unidentified"` | Coroner's inquiries |
| `"Missing person" AND "British Columbia"` | Civil cases, estates |

**Extraction Targets**:
- Suspect movement patterns
- Victim's last known whereabouts
- Timeline discrepancies
- Witness testimony details

**Privacy Considerations**:
- Only public court records are accessed
- No protected or sealed documents
- All sources are audited and logged

---

### 5. Bioinformatics Metadata

> ⚠️ **Important**: Raw DNA sequence data (.fasta, .bam) is **NOT** accessed due to privacy laws. Only phenotypic descriptions from public reports are used.

**Source**: Text descriptions in coroner reports and news releases

**Metadata Types**:

| Type | Example | Use |
|------|---------|-----|
| **Ancestry Estimation** | "European/Indigenous mix" | Population probability scoring |
| **Haplogroup** | "mtDNA haplogroup H" | Maternal lineage clustering |
| **Isotope Results** | "Suggests time in Eastern Canada" | Geographic origin estimation |
| **Phenotype Markers** | "Blue eyes, fair skin" | Physical description matching |

**Processing Approach**:
```python
# Example extraction from narrative text
BIO_METADATA_PATTERNS = {
    "ancestry": r"ancestry\s+(?:estimated|appears?)\s+(?:as|to be)\s+(.+?)(?:\.|,)",
    "haplogroup": r"(?:mt|y)dna\s+haplogroup\s+([A-Z]\d*)",
    "isotope": r"isotope\s+analysis\s+(?:indicates?|suggests?)\s+(.+?)(?:\.|$)"
}
```

---

## Data Refresh Schedule

| Source | Refresh Frequency | Method |
|--------|-------------------|--------|
| BCCS Viewer | Weekly | Automated scraper |
| Canada's Missing | Daily | API polling |
| BC Open Data | Monthly | Bulk download |
| CanLII | Weekly | Search-based scrape |

## Data Quality Assurance

All ingested data is validated for:
- **Completeness**: Required fields present
- **Consistency**: Cross-source validation
- **Currency**: Last-updated timestamps
- **Accuracy**: Geographic coordinate validation


