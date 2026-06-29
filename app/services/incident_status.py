"""Incident status overrides (open / in_process / resolved), JSON-persisted.

The incident queue is derived from the alert stream, so there is no incident
table to update. Operator actions ("Mark in process", "Resolve") are stored as
per-incident overrides in ``var/incident_status.json`` and merged into the
investigation cards on read — surviving process restarts like chat history.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

ALLOWED_STATUSES = {"open", "in_process", "resolved", "escalated"}

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_STORE = _ROOT / "var" / "incident_status.json"

_LOCK = threading.RLock()
_STATUS: dict[str, dict[str, Any]] = {}
_LOADED = False
_STORE_PATH = Path(
    os.environ.get("PITER_INCIDENT_STATUS_PATH", "").strip() or _DEFAULT_STORE
)


def set_store_path(path: str | Path) -> None:
    """Point the store at a new file and force a reload (tests)."""
    global _STORE_PATH, _LOADED
    with _LOCK:
        _STORE_PATH = Path(path)
        _LOADED = False
        _STATUS.clear()


def _ensure_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    with _LOCK:
        if _LOADED:
            return
        _STATUS.clear()
        try:
            raw = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, value in raw.items():
                    if isinstance(value, dict) and value.get("status") in ALLOWED_STATUSES:
                        _STATUS[str(key)] = value
        except (OSError, ValueError):
            pass
        _LOADED = True


def _flush() -> None:
    tmp = _STORE_PATH.with_suffix(".tmp")
    try:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(_STATUS, indent=2), encoding="utf-8")
        os.replace(tmp, _STORE_PATH)
    except OSError:
        pass


def set_status(incident_id: str, status: str) -> dict[str, Any]:
    """Persist a status override for one incident; returns the stored record."""
    iid = (incident_id or "").strip()
    normalized = (status or "").strip().lower()
    if not iid:
        return {"error": "incident_id is required"}
    if normalized not in ALLOWED_STATUSES:
        return {"error": f"status must be one of {sorted(ALLOWED_STATUSES)}"}
    record = {"status": normalized, "updated_at": time.time()}
    with _LOCK:
        _ensure_loaded()
        _STATUS[iid] = record
        _flush()
    return {"incident_id": iid, **record}


def get_status(incident_id: str) -> str | None:
    with _LOCK:
        _ensure_loaded()
        entry = _STATUS.get((incident_id or "").strip())
    return str(entry["status"]) if entry else None


def all_statuses() -> dict[str, str]:
    with _LOCK:
        _ensure_loaded()
        return {k: str(v["status"]) for k, v in _STATUS.items()}
