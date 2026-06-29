"""Conversation history keyed by session_id, persisted to a small JSON store.

History survives a process/container restart: every turn is appended to an
in-memory map AND written through to a JSON file (atomic replace). On first
use (or after :func:`reload`) the map is rehydrated from that file, so a fresh
process serving ``GET /api/history`` returns prior conversations.

Store location: ``PITER_CHAT_HISTORY_PATH`` env var, else ``var/chat_history.json``
under the project root (gitignored — conversation data is never committed).
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

DEFAULT_SESSION_ID = "demo-default"

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_STORE = _ROOT / "var" / "chat_history.json"

_LOCK = threading.RLock()
_MESSAGES: dict[str, list[dict[str, Any]]] = {}
_LOADED = False
_STORE_PATH = Path(
    os.environ.get("PITER_CHAT_HISTORY_PATH", "").strip() or _DEFAULT_STORE
)


def store_path() -> Path:
    """Return the JSON store path currently in use."""
    return _STORE_PATH


def set_store_path(path: str | Path) -> None:
    """Point the store at a new file and force a reload (config/tests)."""
    global _STORE_PATH, _LOADED
    with _LOCK:
        _STORE_PATH = Path(path)
        _LOADED = False
        _MESSAGES.clear()


def _session_id(session_id: str | None) -> str:
    sid = (session_id or "").strip()
    return sid or DEFAULT_SESSION_ID


def _ensure_loaded() -> None:
    """Rehydrate the in-memory map from the JSON store exactly once."""
    global _LOADED
    if _LOADED:
        return
    with _LOCK:
        if _LOADED:
            return
        _MESSAGES.clear()
        _MESSAGES[DEFAULT_SESSION_ID] = []
        if _STORE_PATH.is_file():
            try:
                data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
            if isinstance(data, dict):
                for sid, msgs in data.items():
                    if isinstance(msgs, list):
                        _MESSAGES[str(sid)] = msgs
        _LOADED = True


def reload() -> None:
    """Drop in-memory state and re-read from disk (simulates a restart)."""
    global _LOADED
    with _LOCK:
        _LOADED = False
        _MESSAGES.clear()
    _ensure_loaded()


def _save() -> None:
    """Atomically persist the in-memory map to the JSON store."""
    try:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _STORE_PATH.with_name(_STORE_PATH.name + ".tmp")
        tmp.write_text(json.dumps(_MESSAGES, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_STORE_PATH)
    except OSError:
        # Persistence is best-effort; never break the request path on IO errors.
        pass


def append_turn(
    *,
    session_id: str | None,
    question: str,
    answer: str,
    mode: str | None = None,
) -> None:
    """Record one user/assistant exchange and persist it."""
    _ensure_loaded()
    sid = _session_id(session_id)
    now = time.time()
    with _LOCK:
        bucket = _MESSAGES.setdefault(sid, [])
        bucket.append({"role": "user", "content": question, "ts": now})
        bucket.append({"role": "assistant", "content": answer, "ts": now, "mode": mode})
        _save()


def get_messages(session_id: str | None = None) -> dict[str, Any]:
    """Return chat messages for a session (empty list if none yet)."""
    _ensure_loaded()
    sid = _session_id(session_id)
    with _LOCK:
        messages = list(_MESSAGES.get(sid, []))
    return {
        "session_id": sid,
        "messages": messages,
        "count": len(messages),
    }


def clear_history(session_id: str | None = None) -> dict[str, Any]:
    """Clear chat history for one session or all sessions, then persist."""
    _ensure_loaded()
    sid = (session_id or "").strip()
    with _LOCK:
        if sid:
            removed = len(_MESSAGES.get(sid, []))
            _MESSAGES[sid] = []
            _save()
            return {"session_id": sid, "cleared": removed}
        total = sum(len(v) for v in _MESSAGES.values())
        _MESSAGES.clear()
        _MESSAGES[DEFAULT_SESSION_ID] = []
        _save()
        return {"session_id": None, "cleared": total}


def reset() -> None:
    """Clear all history in memory and on disk (tests)."""
    global _LOADED
    with _LOCK:
        _MESSAGES.clear()
        _MESSAGES[DEFAULT_SESSION_ID] = []
        _LOADED = True
        try:
            if _STORE_PATH.is_file():
                _STORE_PATH.unlink()
        except OSError:
            pass
