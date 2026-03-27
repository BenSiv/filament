import json
from typing import Callable, Iterable


def iter_jsonl(path: str) -> Iterable[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def dedupe_records(records: Iterable[dict], key_fn: Callable[[dict], str | None]) -> list[dict]:
    seen = set()
    deduped = []
    for rec in records:
        key = key_fn(rec)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(rec)
    return deduped


def convert_jsonl_to_json(jsonl_file: str, json_file: str, key_fn: Callable[[dict], str | None]) -> int:
    records = dedupe_records(iter_jsonl(jsonl_file), key_fn)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    return len(records)


def write_json(path: str, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
