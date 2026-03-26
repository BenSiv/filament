import json
import os
import sqlite3
import sys

test_dir = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.dirname(test_dir)
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from scripts import ingest_all_to_fossil as ingest


def _setup_db():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.executescript(ingest.SCHEMA_SQL)
    return conn, cur


def test_insert_note_dedupes_by_content_hash():
    conn, cur = _setup_db()
    ingest.insert_note(cur, "Title A", "Same body", "reddit", source_ref="url-a")
    conn.commit()

    ingest.insert_note(cur, "Title B", "Same body", "reddit", source_ref="url-b")
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM ai_note")
    assert cur.fetchone()[0] == 1

    conn.close()


def test_insert_note_sets_metadata_and_weight():
    conn, cur = _setup_db()
    ingest.insert_note(
        cur,
        "UHR Case",
        "Body text",
        "unidentified",
        source_ref="UP-1",
        metadata={"case_number": "UP-1"},
    )
    conn.commit()

    cur.execute("SELECT metadata, artifact_weight, source_type FROM ai_note")
    meta, weight, source_type = cur.fetchone()

    assert json.loads(meta)["case_number"] == "UP-1"
    assert abs(weight - 0.20) < 1e-6
    assert source_type == "unidentified"

    conn.close()
