# Dual-Track Roadmap: Fossil-SCM + Filament

This roadmap keeps **Fossil-SCM** on the path of a **general self-managed knowledge system**, while **Filament** remains a **domain-specific investigative narrative matching engine**.

## Separation Contract
- **Fossil-SCM** is domain-neutral and must not embed Filament-specific concepts.
- **Filament** owns domain logic (cases, leads, matching) and exports only notes.
- The boundary is a **general knowledge note schema** (title, body, source, metadata).
- **Git is the only VCS** for this repository; Fossil is used only as a knowledge database.

---

## Track A: Fossil-SCM (General Knowledge System)

**Goal:** A durable, self-managed, general-purpose knowledge base with strong capture, retrieval, and auditing workflows.

### A1. Knowledge Capture
**Missing in Fossil-SCM:**
- Stable ingestion abstraction for non-manual sources
- Idempotent ingestion and dedupe conventions
- Standard metadata schema (source, provenance, tags)

**Planned work:**
- Define canonical note schema and metadata guidelines
- Add ingestion helpers (CLI or script) that enforce dedupe by content hash
- Maintain indexes for content hash, source type, and source ref

### A2. Retrieval + Search
**Missing in Fossil-SCM:**
- Verified semantic indexing workflow in current build
- Documented retrieval path (CLI/UI)

**Planned work:**
- Define canonical retrieval flow (CLI and UI)
- Validate or implement semantic indexing step
- Add repository health/status guidance

### A3. UI + Onboarding
**Missing in Fossil-SCM:**
- Minimal onboarding guide for knowledge workflows
- General-purpose note templates/examples

**Planned work:**
- Add a quickstart guide for note capture and retrieval
- Provide neutral sample notes

### A4. Governance + Provenance
**Missing in Fossil-SCM:**
- Provenance conventions (who/when/how a note was added)
- Audit guidelines

**Planned work:**
- Add provenance fields and recommended usage
- Document audit trail expectations

---

## Track B: Filament (Investigative Narrative Matching)

**Goal:** A domain-specific pipeline that ingests, enriches, and matches investigative narratives, then emits structured outputs and knowledge notes.

### B1. Data Enrichment
**Missing in Filament:**
- Broader narrative sources beyond Reddit/NamUs
- Consistent narrative normalization

**Planned work:**
- Add richer sources (news archives, podcasts, case files)
- Normalize narratives into consistent sections

### B2. Matching Intelligence
**Missing in Filament:**
- Unified scoring that blends vector/rule/LLM signals
- Explicit contradictions and evidence weighting

**Planned work:**
- Introduce a consolidated scoring schema
- Expand XAI sections with contradictions and feasibility

### B3. Reporting + Auditability
**Missing in Filament:**
- Reproducible report metadata (inputs, versions, timestamps)
- Report QA checks

**Planned work:**
- Embed report metadata
- Add report consistency checks

### B4. Fossil Integration Boundary
**Missing in Filament:**
- Stable export contract to Fossil
- Tests for ingestion integrity

**Planned work:**
- Define a formal knowledge note contract
- Add ingestion validation tests

---

## Cross-Track Integration (Strict Boundary)
- Filament outputs only general notes into Fossil.
- Fossil remains a neutral knowledge substrate usable by any domain.
- No Filament-specific logic or schema is embedded in Fossil tables.
