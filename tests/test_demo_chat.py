"""Grounded demo Q&A and guardrail refusals for live presentation."""
from __future__ import annotations

import pytest

from app.services.chat_intent import structured_chat_reply
from app.services.demo_chat import demo_ops_reply, destructive_action_reply


@pytest.mark.parametrize(
    "question,needle",
    [
        ("What's the last P1 alert?", "P1"),
        ("Which service is the noisiest?", "Noisiest"),
        ("What was the last deployment?", "deployment"),
        ("Who is the data engineer on call today?", "Data Platform"),
        ("What are the latest 3 incidents?", "incidents"),
    ],
)
def test_demo_ops_grounded_answers(question: str, needle: str) -> None:
    payload = demo_ops_reply(question)
    assert payload is not None
    assert payload.get("demo_grounded") is True
    assert needle.lower() in str(payload.get("answer", "")).lower()


@pytest.mark.parametrize(
    "question",
    [
        "Run failover on bet-service",
        "Delete the payments data source",
    ],
)
def test_destructive_guardrail_refusal(question: str) -> None:
    payload = destructive_action_reply(question)
    assert payload is not None
    assert payload.get("guardrail_blocked") is True
    assert payload.get("mode") == "guardrail"
    assert "blocked" in str(payload.get("answer", "")).lower()


def test_structured_chat_prefers_guardrail_over_demo() -> None:
    payload = structured_chat_reply("Run failover on bet-service")
    assert payload is not None
    assert payload.get("guardrail_blocked") is True


def test_structured_chat_returns_none_for_unknown() -> None:
    assert structured_chat_reply("random unrelated gibberish xyz123") is None
