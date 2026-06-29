"""Load static UI data from app/data/*.json."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent / "data"
_ARCHIVE_DATA = Path(__file__).resolve().parents[1] / "archive" / "legacy-htmx" / "data"


def _load_json(name: str, *, base: Path | None = None) -> Any:
    root = base or _DATA_DIR
    return json.loads((root / name).read_text(encoding="utf-8"))


@lru_cache
def load_example_questions() -> list[dict[str, str]]:
    return _load_json("example_questions.json")


@lru_cache
def load_workflow_alerts() -> list[dict[str, Any]]:
    """Legacy HTMX workflow alerts (archived JSON, tests only)."""
    path = _ARCHIVE_DATA / "workflow_alerts.json"
    if path.is_file():
        return _load_json("workflow_alerts.json", base=_ARCHIVE_DATA)
    return []


def _example_question_text(item: str | dict[str, str]) -> str:
    if isinstance(item, str):
        return item.strip()
    return str(item.get("question") or "").strip()


def flat_example_questions() -> list[str]:
    return [_example_question_text(item) for item in load_example_questions() if _example_question_text(item)]


def grouped_example_questions() -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for item in load_example_questions():
        if isinstance(item, str):
            label, question = "General", item.strip()
        else:
            label = str(item.get("label") or "General")
            question = str(item.get("question") or "").strip()
        if not question:
            continue
        groups.setdefault(label, []).append(question)
    return groups


def find_workflow_alert(alert_id: str | None) -> dict[str, Any] | None:
    if not alert_id:
        return None
    return next((a for a in load_workflow_alerts() if a.get("id") == alert_id), None)
