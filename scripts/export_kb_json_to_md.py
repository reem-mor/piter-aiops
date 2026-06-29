#!/usr/bin/env python3
"""Export knowledge_base/*.json narrative docs to *.md for Bedrock KB sync."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "knowledge_base"
SUBS = ("runbooks", "services", "incidents", "piter")
META_KEYS = (
    "doc_id",
    "title",
    "doc_type",
    "services",
    "environments",
    "severity_applicable",
    "tags",
    "last_updated",
    "author",
    "version",
)


def main() -> int:
    count = 0
    for sub in SUBS:
        for jp in sorted((KB / sub).glob("*.json")):
            data = json.loads(jp.read_text(encoding="utf-8"))
            fm = {k: data[k] for k in META_KEYS if k in data}
            lines = ["---"] + [f'{k}: "{v}"' for k, v in fm.items()] + ["---", "", data.get("body", "")]
            md = jp.with_suffix(".md")
            md.write_text("\n".join(lines), encoding="utf-8")
            print(f"wrote {md.relative_to(ROOT)}")
            count += 1
    print(f"Exported {count} markdown docs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
