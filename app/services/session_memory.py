"""Session store for incident triage and follow-up turns (persisted to JSON).

One session per incident keyed by ``session_id``. Survives process/container restart
via atomic writes to ``var/session_memory.json`` (or ``PITER_SESSION_MEMORY_PATH``).
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_STORE = _ROOT / "var" / "session_memory.json"

_LOCK = threading.RLock()
_SESSIONS: dict[str, dict[str, Any]] = {}
_LOADED = False
_STORE_PATH = Path(
    os.environ.get("PITER_SESSION_MEMORY_PATH", "").strip() or _DEFAULT_STORE
)

_MAX_SESSIONS = 200


def store_path() -> Path:
    return _STORE_PATH


def set_store_path(path: str | Path) -> None:
    global _STORE_PATH, _LOADED
    with _LOCK:
        _STORE_PATH = Path(path)
        _LOADED = False
        _SESSIONS.clear()


def _ensure_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    with _LOCK:
        if _LOADED:
            return
        _SESSIONS.clear()
        if _STORE_PATH.is_file():
            try:
                data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
            if isinstance(data, dict):
                for sid, session in data.items():
                    if isinstance(session, dict):
                        _SESSIONS[str(sid)] = session
        _LOADED = True


def reload() -> None:
    global _LOADED
    with _LOCK:
        _LOADED = False
        _SESSIONS.clear()
    _ensure_loaded()


def _save() -> None:
    try:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _STORE_PATH.with_name(_STORE_PATH.name + ".tmp")
        tmp.write_text(json.dumps(_SESSIONS, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_STORE_PATH)
    except OSError:
        pass


def create_session(alert: dict[str, Any], *, session_id: str | None = None) -> str:
    _ensure_loaded()
    sid = (session_id or "").strip() or str(uuid.uuid4())
    with _LOCK:
        if len(_SESSIONS) >= _MAX_SESSIONS:
            oldest = min(_SESSIONS, key=lambda k: _SESSIONS[k]["created_at"])
            _SESSIONS.pop(oldest, None)
        _SESSIONS[sid] = {
            "session_id": sid,
            "created_at": time.time(),
            "alert": dict(alert),
            "citations": [],
            "tool_outputs": {},
            "triage_card": None,
            "followups": [],
            "post_mortem_draft": None,
        }
        _save()
    return sid


def save_triage(
    session_id: str,
    *,
    citations: list[dict[str, Any]],
    tool_outputs: dict[str, Any],
    triage_card: dict[str, Any],
) -> None:
    _ensure_loaded()
    with _LOCK:
        session = _SESSIONS.get(session_id)
        if session is None:
            return
        session["citations"] = citations
        session["tool_outputs"] = tool_outputs
        session["triage_card"] = triage_card
        _save()


def get_session(session_id: str | None) -> dict[str, Any] | None:
    if not session_id:
        return None
    _ensure_loaded()
    with _LOCK:
        session = _SESSIONS.get(session_id)
        return dict(session) if session is not None else None


def list_sessions(*, limit: int = 50) -> list[dict[str, Any]]:
    """Summaries for incident history UI (newest first)."""
    _ensure_loaded()
    with _LOCK:
        rows: list[dict[str, Any]] = []
        for sid, session in _SESSIONS.items():
            alert = session.get("alert") or {}
            card = session.get("triage_card") or {}
            rows.append(
                {
                    "session_id": sid,
                    "created_at": session.get("created_at"),
                    "alert_id": alert.get("alert_id") or card.get("alert_id"),
                    "timestamp": alert.get("alert_time") or card.get("alert_time"),
                    "severity": alert.get("severity") or card.get("priority"),
                    "service": alert.get("service") or card.get("service"),
                    "environment": alert.get("environment") or card.get("environment"),
                    "symptom": alert.get("symptom") or alert.get("description") or card.get("summary"),
                    "mode": card.get("mode"),
                    "fallback_used": card.get("fallback_used"),
                }
            )
        rows.sort(key=lambda r: float(r.get("created_at") or 0), reverse=True)
        return rows[: max(1, min(limit, 200))]


def save_post_mortem_draft(session_id: str, draft: str) -> bool:
    _ensure_loaded()
    with _LOCK:
        session = _SESSIONS.get(session_id)
        if session is None:
            return False
        session["post_mortem_draft"] = draft.strip()
        _save()
        return True


def get_incident_detail(session_id: str | None) -> dict[str, Any] | None:
    """Full persisted investigation for history drill-down."""
    session = get_session(session_id)
    if session is None:
        return None
    card = session.get("triage_card") or {}
    return {
        "session_id": session["session_id"],
        "created_at": session.get("created_at"),
        "alert": session.get("alert", {}),
        "triage_card": card,
        "citations": session.get("citations", []),
        "tool_outputs": session.get("tool_outputs", {}),
        "followups": list(session.get("followups", [])),
        "post_mortem_draft": session.get("post_mortem_draft"),
    }


def get_history(session_id: str | None) -> dict[str, Any] | None:
    session = get_session(session_id)
    if session is None:
        return None
    return {
        "session_id": session["session_id"],
        "created_at": session["created_at"],
        "alert": session.get("alert", {}),
        "citations": session.get("citations", []),
        "followups": list(session.get("followups", [])),
        "triage_summary": {
            "priority": (session.get("triage_card") or {}).get("priority"),
            "matched_runbook": (session.get("triage_card") or {}).get("matched_runbook"),
            "mode": (session.get("triage_card") or {}).get("mode"),
        },
    }


def append_followup(session_id: str, question: str, answer: dict[str, Any]) -> bool:
    _ensure_loaded()
    with _LOCK:
        session = _SESSIONS.get(session_id)
        if session is None:
            return False
        session["followups"].append({"question": question, "answer": answer, "ts": time.time()})
        _save()
        return True


def reset() -> None:
    global _LOADED
    with _LOCK:
        _SESSIONS.clear()
        _LOADED = True
        try:
            if _STORE_PATH.is_file():
                _STORE_PATH.unlink()
        except OSError:
            pass
