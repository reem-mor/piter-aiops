"""Knowledge Base manifest for SPA listing and retrieval tester."""
from __future__ import annotations

from app.services.kb_corpus import load_kb_manifest

__all__ = ["load_kb_manifest", "kb_sections"]


def kb_sections() -> dict[str, list[dict]]:
    manifest = load_kb_manifest()
    sections: dict[str, list[dict]] = {
        "runbooks": [],
        "environments": [],
        "policies": [],
        "incidents": [],
        "glossary": [],
        "services": [],
        "guides": [],
    }
    for doc in manifest:
        dtype = doc.get("doc_type", "runbook")
        key = {
            "runbook": "runbooks",
            "policy": "policies",
            "incident": "incidents",
            "service": "services",
            "guide": "guides",
            "environment": "environments",
            "glossary": "glossary",
            "reference": "policies",
        }.get(dtype, "runbooks")
        sections.setdefault(key, []).append(doc)
    return sections
