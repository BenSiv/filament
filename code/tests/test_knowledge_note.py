import os
import sys

import pytest

test_dir = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.dirname(test_dir)
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from core.knowledge_note import content_hash, normalize_note


def test_normalize_note_trims_title_and_requires_fields():
    note = normalize_note(
        title="A" * 300,
        body="Body text",
        source_type="generic",
        source_ref="ref",
        tier=1,
        metadata={"k": "v"},
    )
    assert len(note["title"]) == 200
    assert note["body"] == "Body text"
    assert note["source_type"] == "generic"

    with pytest.raises(ValueError):
        normalize_note(title="", body="Body", source_type="generic")


def test_content_hash_is_stable():
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abcd")
