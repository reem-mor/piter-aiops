#!/usr/bin/env python3
"""Print demo questions as plain text for presenters."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    questions = json.loads((ROOT / "evaluation" / "demo_questions.json").read_text(encoding="utf-8"))
    for item in questions:
        print(f"{item['id']}: {item['question']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
