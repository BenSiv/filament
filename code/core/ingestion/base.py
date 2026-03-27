from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable
import json
import os
from datetime import datetime, timezone


@dataclass
class IngestedRecord:
    title: str
    body: str
    source_type: str
    source_ref: str
    metadata: dict[str, Any] = field(default_factory=dict)
    process_level: str = "raw"

    def to_json(self) -> str:
        payload = {
            "title": self.title,
            "body": self.body,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "metadata": self.metadata,
            "process_level": self.process_level,
        }
        return json.dumps(payload, ensure_ascii=True)


class IngestionSource:
    name: str = ""
    description: str = ""
    default_enabled: bool = False

    def fetch(self, limit: int | None = None) -> Iterable[IngestedRecord]:
        raise NotImplementedError

    def run(self, output_dir: str, limit: int | None = None) -> int:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = os.path.join(output_dir, f"{self.name}_{timestamp}.jsonl")

        count = 0
        with open(out_path, "w", encoding="utf-8") as f:
            for record in self.fetch(limit=limit):
                f.write(record.to_json() + "\n")
                count += 1

        return count
