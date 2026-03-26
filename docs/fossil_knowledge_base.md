# Fossil AI Knowledge Base

This document describes the Fossil-backed knowledge base used for narrative RAG workflows.

## What It Is
- **Fossil repo DB** (`data/knowledge.fossil`) stores AI note tables for narrative content.
- Filament ingests structured case data + Reddit narratives into these tables.
- Fossil can then drive UI and retrieval workflows on top of those notes.
- **Git is the only VCS for this repo.** Fossil is used strictly as a local knowledge
  database and should not manage source code history here.

## Quick Start

```bash
# Initialize repository
fossil init data/knowledge.fossil
fossil open data/knowledge.fossil data/knowledge_workspace

# Enable AI tables (safe if already enabled)
fossil ai init -R data/knowledge.fossil
fossil ai status -R data/knowledge.fossil

# Ingest all Filament data
python3 code/scripts/ingest_all_to_fossil.py
```

## What Gets Ingested
- Unidentified Human Remains (UHR) cases from `data/filament.db`
- Missing persons from `data/filament.db`
- Reddit narratives from `data/raw/reddit/missing_and_uhr_narratives.json`
- AI-generated leads from `data/reports/reddit_sleuth_leads.json`

## Schema Notes
Filament writes to Fossil's AI tables (`ai_note`, `ai_vector`, etc.).
- Inserts are **idempotent** by content hash.
- Indexes are added to speed dedupe and retrieval lookups.

## Verification

```bash
# Check AI tables are present
fossil ai status -R data/knowledge.fossil

# Confirm notes exist
sqlite3 data/knowledge.fossil "SELECT COUNT(*) FROM ai_note;"
```

## Optional Semantic Indexing
Some custom Fossil builds include semantic indexing commands (e.g. `fossil agent semantic-index`).
If your build supports this, run it after ingestion.

## Troubleshooting
- **"current directory is not within an open check-out"**
  - Ensure the workspace exists and is opened:
  - `fossil open data/knowledge.fossil data/knowledge_workspace`
- **Missing AI tables**
  - Run `fossil ai init -R data/knowledge.fossil`
- **Ollama errors**
  - Ensure Ollama is running locally and the configured models are installed.
