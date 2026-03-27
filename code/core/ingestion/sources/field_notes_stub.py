from __future__ import annotations

import json
import os
from typing import Iterable

from ..base import IngestedRecord, IngestionSource
from ..registry import REGISTRY


@REGISTRY.register
class FieldNotesStub(IngestionSource):
    name = "field_notes"
    description = "Stub for investigator field notes or local uploads."
    default_enabled = False

    def fetch(self, limit: int | None = None) -> Iterable[IngestedRecord]:
        data_path = "data/raw/sources/field_notes_stub.jsonl"
        if not os.path.exists(data_path):
            return []
        records = []
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                payload = json.loads(line)
                records.append(
                    IngestedRecord(
                        title=payload.get("title", ""),
                        body=payload.get("body", ""),
                        source_type="field_notes",
                        source_ref=payload.get("source_ref", ""),
                        metadata=payload.get("metadata", {}),
                    )
                )
                if limit and len(records) >= limit:
                    break
        return records
