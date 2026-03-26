# Knowledge Note Contract

This contract defines the neutral schema used to exchange notes between Filament and Fossil.
It is intentionally domain-agnostic.

## Required Fields
- **title**: Short, human-readable summary (max 200 chars)
- **body**: Full text content
- **source_type**: General category (e.g., `reddit`, `lead`, `missing_person`, `unidentified`)

## Optional Fields
- **source_ref**: External reference string or URL
- **tier**: Integer importance/priority
- **process_level**: Pipeline stage (default `raw`)
- **metadata**: JSON-serializable map with neutral keys

## Constraints
- Title and body must be non-empty
- Metadata must be JSON-serializable
- Dedupe is performed on a content hash of the body

## Usage
Filament builds notes according to this contract and writes them into Fossil AI tables.
Fossil remains domain-neutral and does not encode Filament-specific logic.
