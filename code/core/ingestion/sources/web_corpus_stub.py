from __future__ import annotations

import json
import os
from typing import Iterable

from ..base import IngestedRecord, IngestionSource
from ..registry import REGISTRY


@REGISTRY.register
class WebCorpusStub(IngestionSource):
    name = "web_corpus"
    description = "Stub for curated web corpus ingestion (manual URL dumps)."
    default_enabled = False

    def fetch(self, limit: int | None = None) -> Iterable[IngestedRecord]:
        data_path = "data/raw/sources/web_corpus_stub.jsonl"
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
                        source_type="web_corpus",
                        source_ref=payload.get("source_ref", ""),
                        metadata=payload.get("metadata", {}),
                    )
                )
                if limit and len(records) >= limit:
                    break
        return records
