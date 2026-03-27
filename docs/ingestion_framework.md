# External Ingestion Framework

This framework defines a pluggable ingestion layer for external text sources.
It is intentionally offline-first and ships with stubs you can replace with
real scrapers later.

## Goals
- Provide a consistent contract for ingesting large volumes of text.
- Keep sources modular and easy to swap or extend.
- Write raw records to JSONL for downstream processing.

## Structure
- `code/core/ingestion/base.py` defines the record schema and source interface.
- `code/core/ingestion/registry.py` registers available sources.
- `code/core/ingestion/sources/` contains source stubs.
- `code/scripts/ingest_external.py` runs sources and writes JSONL output.

## Output Format
Each record is written as JSON per line with:
- `title`
- `body`
- `source_type`
- `source_ref`
- `metadata`
- `process_level`

## Current Stub Sources
- `news` — news archives and press coverage
- `public_records` — coroner/ME, court records, FOIA
- `podcasts` — transcripts and episode summaries
- `web_corpus` — curated URL dumps
- `field_notes` — investigator notes or uploads

## Usage
List sources:
```bash
python3 code/scripts/ingest_external.py --list
```

Run one or more sources:
```bash
python3 code/scripts/ingest_external.py --source news --source public_records
```

Run all stubs (writes empty files until real scrapers are added):
```bash
python3 code/scripts/ingest_external.py --all
```

Outputs land in `data/raw/ingestion/` as timestamped JSONL files.

## Next Steps
Replace a stub by implementing `fetch()` and returning `IngestedRecord`
instances. Keep source-specific data in `metadata` and store only neutral
fields at the top level.
