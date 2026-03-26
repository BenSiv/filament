# Knowledge Flow Strategy (Fossil Knowledge Base + Filament)

## Purpose
Define a comprehensive, implementation-aligned knowledge flow that uses Fossil
as the knowledge database (notes, provenance, retrieval, vectors) while Filament
remains the investigative pipeline and lead generator. Git remains the sole VCS.

## Target Outcomes
- Ingest vast volumes of unstructured and semi-structured text.
- Organize knowledge with provenance, dedupe, and tiered curation.
- Enable retrieval and AI-assisted workflows to generate investigative leads.
- Maintain auditability from lead back to sources.

## System Boundary
- **Git**: version control for the Filament codebase.
- **Fossil**: knowledge database for AI notes, vectors, retrieval, and review.
- **Filament**: ingestion, enrichment, matching, and lead generation.

## Knowledge Layers (Mapped to Fossil Tiers)
- **Tier 0 (Fleeting / Raw)**: raw narratives, scraped texts, unfiltered case data.
- **Tier 1 (Working)**: cleaned, normalized, and lightly structured notes.
- **Tier 2 (Draft)**: synthesized summaries, candidate leads, merged narratives.
- **Tier 3 (Atomic / Durable)**: canonical, single-subject notes or durable artifacts.

## Process Levels
Process levels allow sub-staging independent of tier:
- `raw`: unprocessed or minimally processed text.
- `normalized`: cleaned, deduped, lightly structured.
- `enriched`: entities, timelines, and facts extracted.
- `lead_candidate`: synthesis intended for investigative follow-up.
- `promoted`: reviewed and durable.

## End-to-End Flow

### 1) Capture (Ingestion)
- Inputs: case DB, narratives, documents, tips, news, external datasets.
- Write to `ai_note` with:
  - `tier=0`, `process_level=raw`
  - `source_type`, `source_ref`, `metadata` (source URL, timestamps, pipeline version)
  - `content_hash` for dedupe
- Link raw notes to their source artifacts using `source_ref`.

### 2) Normalize + Structure
- Create new notes from raw sources:
  - `tier=1`, `process_level=normalized`
- Preserve provenance by linking to raw notes in `ai_note_link` with `link_type=derived_from`.
- Record extraction stats and schema version in `metadata`.

### 3) Enrich + Synthesize
- Generate enriched notes and summaries:
  - `tier=1` or `tier=2`, `process_level=enriched`
- Link to supporting notes with `ai_note_link` (e.g., `supports`, `summarizes`).
- Use `metadata` for entity counts, timeline coverage, and extraction confidence.

### 4) Retrieval (Context Assembly)
- Each lead search or investigative query writes:
  - `ai_retrieval` (query metadata)
  - `ai_retrieval_note` (ranked results, scores, tier weights)
- Reinforce retrieval weights for notes that are repeatedly useful.

### 5) Lead Generation
- Produce lead notes:
  - `tier=2`, `process_level=lead_candidate`
- Link to all supporting evidence notes in `ai_note_link`.
- Store confidence, rationale summary, and model version in `metadata`.

### 6) Review + Promotion
- Write `ai_review` entries for promotion decisions:
  - atomicity, duplication, connectivity, and promotion status
- Promote to Tier 3 when leads become durable knowledge.
- Materialize durable artifacts as Fossil wiki pages or a `knowledge/` file tree.

## Retrieval + Vector Indexing
- Use `ai_vector` for semantic indexing (via Fossil `agent semantic-index` if available).
- Maintain text retrieval as a first-class fallback for transparency and stability.

## Provenance and Auditability
Every lead or promoted artifact should trace back to:
- original source notes
- retrieval events that surfaced the evidence
- review decisions that led to promotion

## Operational Checks (Minimum Viable)
- Verify AI tables exist: `fossil ai status -R data/knowledge.fossil`
- Validate note contract and metadata serialization.
- Periodically report:
  - note counts by tier
  - retrieval events per week
  - duplicates and merges
  - promotion rate to Tier 3

## Immediate Implementation Priorities
1. Extend ingestion to write `ai_note_link` for raw → normalized → enriched chains.
2. Add retrieval logging into `ai_retrieval` and `ai_retrieval_note` for every lead run.
3. Add a small review pass that writes `ai_review` for candidate leads.
4. Define a lightweight promotion workflow for durable artifacts (wiki or `knowledge/`).

## Non-Goals
- Do not alter Fossil’s core development trajectory.
- Avoid Filament-specific schema changes in Fossil tables.
- Keep all Filament-specific semantics in `metadata` and Filament code.
