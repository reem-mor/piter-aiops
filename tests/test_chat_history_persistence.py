"""Chat history must survive a process restart (Phase 3)."""
from __future__ import annotations

from app.services import chat_history


def test_history_survives_restart(tmp_path):
    store = tmp_path / "chat_history.json"
    chat_history.set_store_path(store)
    chat_history.reset()

    chat_history.append_turn(
        session_id="sess-A", question="who owns bet-service?", answer="Betting Core"
    )
    chat_history.append_turn(
        session_id="sess-A", question="and the on-call?", answer="Primary Betting Core On-Call"
    )
    assert store.is_file()

    # Simulate a fresh process: drop memory, rehydrate from disk only.
    chat_history.reload()

    out = chat_history.get_messages("sess-A")
    assert out["count"] == 4
    assert out["messages"][0]["content"] == "who owns bet-service?"
    assert out["messages"][-1]["content"] == "Primary Betting Core On-Call"


def test_history_keyed_by_session(tmp_path):
    chat_history.set_store_path(tmp_path / "chat_history.json")
    chat_history.reset()
    chat_history.append_turn(session_id="s1", question="q1", answer="a1")
    chat_history.append_turn(session_id="s2", question="q2", answer="a2")
    chat_history.reload()
    assert chat_history.get_messages("s1")["count"] == 2
    assert chat_history.get_messages("s2")["count"] == 2
    assert chat_history.get_messages("s3")["count"] == 0
