#!/usr/bin/env python3
"""One-time migration: knowledge_base/*.md -> *.json, drop duplicates, build catalog."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.kb_corpus import (  # noqa: E402
    KB_ROOT,
    STRUCTURED_INDEX_NAME,
    write_catalog_csv,
)

# Narrative already covered by data/source/ — do not duplicate in the KB corpus.
SKIP_MD = {
    "business_impact/business_impact_matrix.md",
    "escalation/escalation_policy.md",
}


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"')
    body = text[end + 5 :].lstrip("\n")
    return meta, body


def _structured_index() -> dict:
    return {
        "doc_id": "structured_data_index",
        "title": "Structured operational datasets (Action Groups)",
        "doc_type": "reference",
        "services": "all",
        "environments": "all",
        "severity_applicable": "P1,P2,P3,P4",
        "tags": "csv, json, action-groups, no-duplicate",
        "last_updated": "2026-06-09",
        "author": "PITER AiOps",
        "version": "1.0",
        "body": (
            "Structured operational data is stored once under data/source/ and read by "
            "Bedrock Action Groups (not duplicated in this knowledge base).\n\n"
            "- deploys.csv -> piter-recent-deployments\n"
            "- service_owners.csv, business_impact.json -> piter-service-context\n"
            "- past_incidents.csv -> piter-similar-incidents\n"
            "- escalation_policies.json, priority_matrix.json -> piter-escalation\n\n"
            "Use Action Groups for numeric scores, owners, and historical rows. Use KB JSON "
            "runbooks and service guides for procedural remediation text."
        ),
        "datasets": [
            {"file": "data/source/deploys.csv", "tool": "piter-recent-deployments"},
            {"file": "data/source/service_owners.csv", "tool": "piter-service-context"},
            {"file": "data/source/business_impact.json", "tool": "piter-service-context"},
            {"file": "data/source/past_incidents.csv", "tool": "piter-similar-incidents"},
            {"file": "data/source/escalation_policies.json", "tool": "piter-escalation"},
            {"file": "data/source/priority_matrix.json", "tool": "piter-escalation"},
        ],
    }


def main() -> int:
    if not KB_ROOT.is_dir():
        print(f"Missing {KB_ROOT}")
        return 1

    converted = 0
    skipped = 0
    for md_path in sorted(KB_ROOT.rglob("*.md")):
        rel = md_path.relative_to(KB_ROOT).as_posix()
        if rel in SKIP_MD:
            md_path.unlink()
            skipped += 1
            print(f"SKIP+DELETE duplicate {rel}")
            continue
        meta, body = _parse_front_matter(md_path.read_text(encoding="utf-8-sig"))
        doc_id = md_path.stem
        payload = {
            "doc_id": doc_id,
            "title": meta.get("title", doc_id.replace("_", " ").title()),
            "doc_type": meta.get("doc_type", "runbook"),
            "services": meta.get("services", ""),
            "environments": meta.get("environments", ""),
            "severity_applicable": meta.get("severity_applicable", ""),
            "tags": meta.get("tags", ""),
            "last_updated": meta.get("last_updated", "2026-06-09"),
            "author": meta.get("author", "PITER AiOps"),
            "version": meta.get("version", "1.0"),
            "body": body.strip(),
        }
        json_path = md_path.with_suffix(".json")
        json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        md_path.unlink()
        converted += 1
        print(f"CONVERT {rel} -> {json_path.relative_to(KB_ROOT).as_posix()}")

    index_path = KB_ROOT / STRUCTURED_INDEX_NAME
    index_path.write_text(
        json.dumps(_structured_index(), indent=2) + "\n",
        encoding="utf-8",
    )
    catalog = write_catalog_csv()
    print(f"Wrote {catalog.relative_to(ROOT)} ({converted} docs, {skipped} duplicates removed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
