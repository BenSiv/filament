# Data Provenance & Legal Compliance

## Data Sources Used

### 1. BC Coroners Service - Unidentified Human Remains (UHR)
- **Source**: BC Data Catalogue (Official Government Open Data Portal)
- **Dataset**: "Unidentified Human Remains BC" (ID: `8faed535-7fb6-476f-8d0d-0141f4da8d70`)
- **Access Method**: ArcGIS REST API (FeatureServer/query)
- **License**: [Open Government Licence - British Columbia](https://www2.gov.bc.ca/gov/content/data/open-data/open-government-licence-bc)
- **Legal Status**: ✅ Fully compliant - explicitly published for public use

### 2. BC City Coordinates
- **Source**: Common geographic knowledge / Wikipedia
- **Data**: 18 major BC cities with lat/lon coordinates and population
- **Legal Status**: ✅ Public domain factual information

## Data NOT Used (Would Require Permission)

### NCMPUR / Canada's Missing
- **Status**: Website accessible but no official API
- **Action**: NOT scraped - requires proper data sharing agreement with RCMP
- **Future**: Request formal access through proper channels

### CanLII Legal Documents
- **Status**: Rate-limited, terms of service require review
- **Action**: NOT scraped pending TOS review
- **Future**: Apply for API access or use only permitted methods

## Compliance Principles

1. **Only use official APIs** - No screen scraping of protected content
2. **Respect robots.txt** - Check before any automated access
3. **Honor rate limits** - Implement appropriate delays
4. **Cite sources** - Document all data provenance
5. **Open licenses only** - Verify license permits intended use
