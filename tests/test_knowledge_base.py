"""Validate the organized Knowledge Base structure (JSON + catalog CSV)."""
from __future__ import annotations

import csv
from pathlib import Path

from app.services.kb_corpus import (
    CATALOG_PATH,
    KB_ROOT,
    REQUIRED_DOC_KEYS,
    VALID_DOC_TYPES,
    iter_corpus_json_paths,
    load_kb_document,
)

REQUIRED_DIRS = {"runbooks", "incidents", "services", "piter"}


def test_knowledge_base_has_authoritative_sections():
    assert REQUIRED_DIRS <= {path.name for path in KB_ROOT.iterdir() if path.is_dir()}


def test_knowledge_base_json_has_required_fields():
    docs = list(iter_corpus_json_paths())
    assert docs
    for path in docs:
        doc = load_kb_document(path)
        assert REQUIRED_DOC_KEYS <= set(doc), f"{path} missing keys"
        assert doc["doc_type"] in VALID_DOC_TYPES


def test_knowledge_base_catalog_csv_is_outside_kb_prefix_and_matches_corpus():
    catalog_path = CATALOG_PATH
    assert catalog_path.is_file()
    # The catalog must NOT live under the KB prefix (it is a structured index).
    assert KB_ROOT not in catalog_path.parents
    with catalog_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    json_ids = {load_kb_document(p)["doc_id"] for p in iter_corpus_json_paths()}
    catalog_ids = {row["doc_id"] for row in rows}
    assert json_ids == catalog_ids


def test_knowledge_base_keeps_safety_guidance_in_corpus():
    kb_text = "\n".join(load_kb_document(p)["body"] for p in iter_corpus_json_paths())
    assert "real phone numbers" in kb_text or "personal email" in kb_text.lower()
    assert "PITER_NOTIFICATION_MODE=live" not in kb_text
