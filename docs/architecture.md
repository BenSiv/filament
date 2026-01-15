# System Architecture

FILAMENT uses a **Hybrid Retrieval-Augmented Generation (RAG)** architecture that treats text and biological metadata as connected nodes in a knowledge graph rather than isolated records.

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Ingestion["Data Ingestion Layer"]
        direction LR
        Scraper[Web Scrapers]
        Parser[Document Parsers]
        API[API Clients]
    end
    
    subgraph Processing["Processing Layer"]
        direction TB
        Extract[Entity Extraction<br/>LlamaIndex + Unstract]
        Embed[Embedding Generation<br/>sentence-transformers]
        Structure[Schema Mapping]
    end
    
    subgraph Storage["Storage Layer"]
        direction LR
        PG[(PostgreSQL<br/>+ pgvector)]
        Neo[(Neo4j<br/>Knowledge Graph)]
    end
    
    subgraph Analysis["Analysis Layer"]
        direction TB
        Vector[Vector Search]
        Graph[Graph Traversal]
        LLM[LLM Reasoning<br/>Ollama]
    end
    
    subgraph Output["Output Layer"]
        Matches[Match Candidates]
        Viz[Kepler.gl Maps]
        Report[Case Reports]
    end
    
    Ingestion --> Processing
    Processing --> Storage
    Storage --> Analysis
    Analysis --> Output
```

## Core Components

### 1. Data Ingestion Layer

Responsible for acquiring data from heterogeneous sources:

| Component | Purpose | Sources |
|-----------|---------|---------|
| **Web Scrapers** | Extract data from public GIS viewers | BCCS Viewer, BC Open Data |
| **Document Parsers** | Process PDFs and legal documents | CanLII, Coroner reports |
| **API Clients** | Interface with structured APIs | NCMPUR, BC Data Catalogue |

### 2. Processing Layer

Transforms raw data into queryable entities:

- **Entity Extraction**: LLM-powered extraction of structured facts from narrative text
- **Embedding Generation**: Vector representations for semantic search
- **Schema Mapping**: Normalize entities to unified data model

### 3. Storage Layer

Dual-database architecture for complementary query patterns:

```mermaid
erDiagram
    PERSON ||--o{ LOCATION : "located_at"
    PERSON ||--o{ PHYSICAL_FEATURE : "has_feature"
    PERSON ||--o{ CLOTHING : "wearing"
    PERSON ||--o{ BIO_EVIDENCE : "has_evidence"
    LOCATION ||--o{ EVENT : "site_of"
    
    PERSON {
        uuid id PK
        string case_number
        string source
        date discovered_date
        vector embedding
    }
    
    LOCATION {
        uuid id PK
        point coordinates
        string region
        string description
    }
    
    PHYSICAL_FEATURE {
        uuid id PK
        string feature_type
        string description
        float confidence
    }
```

### 4. Analysis Layer

Multi-modal search and reasoning:

- **Vector Search**: Semantic similarity matching (e.g., "bunnyhug" ↔ "hooded sweatshirt")
- **Graph Traversal**: Find connections through shared attributes
- **LLM Reasoning**: Generate match hypotheses with explainable reasoning

## Data Flow

```mermaid
sequenceDiagram
    participant S as Data Source
    participant I as Ingestion
    participant P as Processing
    participant DB as Storage
    participant A as Analysis
    participant U as User
    
    S->>I: Raw data (HTML, PDF, JSON)
    I->>P: Parsed documents
    P->>P: Extract entities
    P->>P: Generate embeddings
    P->>DB: Store entities + vectors
    
    U->>A: Search query
    A->>DB: Vector similarity search
    A->>DB: Graph pattern match
    A->>A: LLM reasoning
    A->>U: Ranked match candidates
```

## Privacy-First Design

```mermaid
flowchart LR
    subgraph External["External (Public Only)"]
        Sources[Public Data Sources]
    end
    
    subgraph Internal["Internal (Air-Gapped Option)"]
        LLM[Local LLM<br/>Ollama]
        DB[(Local Database)]
        App[Application]
    end
    
    Sources -->|HTTPS| App
    App <--> DB
    App <--> LLM
```

Key privacy measures:
- All LLM inference runs locally via Ollama
- No raw DNA data processed - only phenotypic metadata
- Audit logging for all match operations
- Optional air-gapped deployment

## Deployment Options

| Option | Use Case | Components |
|--------|----------|------------|
| **Local Development** | Research & prototyping | SQLite, Ollama, single machine |
| **Lab Deployment** | Investigation team | PostgreSQL, Neo4j, internal network |
| **Secure Production** | Operational use | Air-gapped, encrypted storage, audit logging |
