"""Load and summarize the deterministic alert storm CSV for demo APIs."""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from app.services import data_access

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STREAM_PATH = ROOT / "data" / "source" / "alert_stream.csv"

WARNING_SHOT_PREFIX = "ALT-DEMO-WARN-"
ACTIVE_ALERT_LIMIT = 15


@lru_cache(maxsize=1)
def _load_rows(path: str | None = None) -> tuple[dict[str, str], ...]:
    csv_path = Path(path) if path else DEFAULT_STREAM_PATH
    if not csv_path.is_file():
        return ()
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


def load_alert_stream(path: str | None = None) -> list[dict[str, str]]:
    return list(_load_rows(path))


def _is_noise(row: dict[str, str]) -> bool:
    return str(row.get("is_noise_candidate", "")).lower() == "true"


def _is_p1_trigger(row: dict[str, str]) -> bool:
    return row.get("severity") == "P1" or str(row.get("is_trigger", "")).lower() == "true"


def load_active_alerts(path: str | None = None, *, limit: int = ACTIVE_ALERT_LIMIT) -> list[dict[str, str]]:
    """Return 10–15 non-noise alerts plus the deterministic P1 trigger row."""
    rows = load_alert_stream(path)
    if not rows:
        return []

    pd = None
    if data_access.pandas_available():
        try:
            import pandas as pd  # type: ignore[no-redef]
        except ImportError:
            pd = None
    if pd is not None:
        frame = pd.DataFrame(rows)
        if "is_noise_candidate" in frame.columns:
            frame = frame[frame["is_noise_candidate"].astype(str).str.lower() != "true"]
        non_p1 = frame[~frame.apply(lambda r: _is_p1_trigger(r.to_dict()), axis=1)]
        p1_rows = frame[frame.apply(lambda r: _is_p1_trigger(r.to_dict()), axis=1)]
        picked = non_p1.head(max(1, limit - 1))
        result = [r.to_dict() for _, r in picked.iterrows()]
        if not p1_rows.empty:
            result.append(p1_rows.iloc[0].to_dict())
        return result[:limit]

    non_noise = [r for r in rows if not _is_noise(r)]
    p1 = next((r for r in non_noise if _is_p1_trigger(r)), None)
    pre_p1 = [r for r in non_noise if not _is_p1_trigger(r)]
    cap = max(1, limit - (1 if p1 else 0))
    result = pre_p1[:cap]
    if p1:
        result.append(p1)
    return result[:limit]


def summarize_alert_stream(path: str | None = None) -> dict:
    rows = load_alert_stream(path)
    active = load_active_alerts(path)
    by_severity: dict[str, int] = {}
    for row in rows:
        sev = row.get("severity", "P4")
        by_severity[sev] = by_severity.get(sev, 0) + 1

    noise_count = sum(1 for r in rows if _is_noise(r))
    p1_rows = [r for r in rows if _is_p1_trigger(r)]
    warning_rows = [r for r in rows if str(r.get("alert_id", "")).startswith(WARNING_SHOT_PREFIX)]

    return {
        "total": len(rows),
        "label": f"Alert storm corpus ({len(rows)} alerts)",
        "duration_seconds": 300,
        "by_severity": by_severity,
        "noise_suppressed": noise_count,
        "active_count": len(active),
        "active_alerts": active,
        "warning_signals": len(warning_rows),
        "p1_trigger": p1_rows[0] if p1_rows else None,
        "p1_count": len(p1_rows),
    }


def p1_demo_alert(path: str | None = None) -> dict:
    """Build a triage payload from the deterministic P1 trigger row."""
    summary = summarize_alert_stream(path)
    trigger = summary.get("p1_trigger") or {}
    if not trigger:
        return {
            "alert_id": "ALT-DEMO-P1-001",
            "service": "bet-service",
            "environment": "GIB-UKGC",
            "severity": "P1",
            "symptom": "CRITICAL: bet-service nodes unresponsive — 100% error rate on GIB-UKGC",
            "description": "CRITICAL: bet-service nodes unresponsive — 100% error rate on GIB-UKGC",
            "alert_time": "2026-06-10T10:02:55.000Z",
            "duration_minutes": 45,
        }
    return {
        "alert_id": trigger.get("alert_id", "ALT-DEMO-P1-001"),
        "service": trigger.get("service", "bet-service"),
        "environment": trigger.get("environment", "GIB-UKGC"),
        "severity": trigger.get("severity", "P1"),
        "symptom": trigger.get("title", trigger.get("symptom", "")),
        "description": trigger.get("title", trigger.get("description", "")),
        "alert_time": trigger.get("timestamp", "2026-06-10T10:02:55.000Z"),
        "duration_minutes": 45,
    }
