# FILAMENT System Data Flow

```mermaid
flowchart TD
    subgraph Sources
        NamUs[NamUs Website]
    end

    subgraph Scrapers
        S_MP[scrape_namus_missing.py]
        S_UHR[scrape_namus_unidentified.py]
    end

    subgraph Raw_Data [Raw Data Storage]
        JSON_MP[data/raw/namus_missing.json]
        JSON_UHR[data/raw/namus_unidentified.json]
    end

    subgraph Processing
        P_Flat[preprocess_mp.py]
        P_Load[load_namus_to_db.py]
        Embed[SentenceTransformer<br/>(all-MiniLM-L6-v2)]
    end

    subgraph Derived_Data [Processed Data]
        Flat_MP[namus_missing_flat.json]
        Flat_UHR[namus_unidentified_flat.json]
    end

    subgraph Database [PostgreSQL + pgvector]
        DB_MP[(Table: missing_persons)]
        DB_UHR[(Table: unidentified_cases)]
    end

    subgraph Matchers [Matching Engines]
        M_Rule[match_cases.py<br/>(Rule-Based + Keyword)]
        M_Rich[find_rich_leads.py<br/>(Rare Word Overlap)]
        M_RAG[match_rag.py<br/>(Vector Similarity)]
    end

    subgraph Outputs [Reports & Case Studies]
        Leads[data/processed/leads.json]
        Report_Leads[leads_report.md]
        Report_Study[Case Study Markdown<br/>(e.g. Richard Frye)]
    end

    %% Flows
    NamUs --> S_MP
    NamUs --> S_UHR

    S_MP --> JSON_MP
    S_UHR --> JSON_UHR

    %% Flattening Path
    JSON_MP --> P_Flat
    JSON_UHR --> P_Flat
    P_Flat --> Flat_MP
    P_Flat --> Flat_UHR

    %% DB Path
    JSON_MP --> P_Load
    JSON_UHR --> P_Load
    P_Load -- Generate Embeddings --> Embed
    Embed --> P_Load
    P_Load --> DB_MP
    P_Load --> DB_UHR

    %% Matching Paths
    Flat_MP & Flat_UHR --> M_Rule
    M_Rule --> Leads
    Leads --> M_Rich
    M_Rich -- "Refined Ranking" --> Leads

    DB_MP & DB_UHR --> M_RAG

    %% Reporting
    Leads --> Report_Leads
    M_Rich & M_RAG --> Report_Study

```
