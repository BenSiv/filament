import hashlib
import json

MAX_TITLE_LEN = 200
ALLOWED_NOTE_KEYS = {
    "title",
    "body",
    "source_type",
    "source_ref",
    "tier",
    "process_level",
    "metadata",
}


def content_hash(body: str) -> str:
    return hashlib.sha1(body.encode("utf-8", errors="replace")).hexdigest()


def normalize_note(
    title: str,
    body: str,
    source_type: str,
    source_ref: str = "",
    tier: int = 0,
    metadata: dict | None = None,
    process_level: str = "raw",
) -> dict:
    if not title or not title.strip():
        raise ValueError("title is required")
    if not body or not body.strip():
        raise ValueError("body is required")
    if not source_type or not source_type.strip():
        raise ValueError("source_type is required")

    note = {
        "title": title.strip()[:MAX_TITLE_LEN],
        "body": body,
        "source_type": source_type.strip(),
        "source_ref": source_ref or "",
        "tier": int(tier),
        "process_level": process_level,
        "metadata": metadata or {},
    }
    validate_note_contract(note)
    return note


def validate_note_contract(note: dict) -> None:
    missing = [key for key in ("title", "body", "source_type") if not note.get(key)]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    extra = [key for key in note.keys() if key not in ALLOWED_NOTE_KEYS]
    if extra:
        raise ValueError(f"unsupported note fields: {', '.join(sorted(extra))}")

    try:
        json.dumps(note.get("metadata", {}), ensure_ascii=True, sort_keys=True)
    except TypeError as exc:
        raise ValueError("metadata must be JSON-serializable") from exc


def serialize_metadata(metadata: dict) -> str:
    return json.dumps(metadata, ensure_ascii=True, sort_keys=True)
