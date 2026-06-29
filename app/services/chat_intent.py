"""Lightweight intent guard for /api/chat — greetings, demo Q&A, and guardrails."""
from __future__ import annotations

import re
from typing import Any

from app.services.demo_chat import demo_ops_reply, destructive_action_reply

_GREETING = re.compile(
    r"^(?:hi|hello|hey|yo|howdy|good\s+(?:morning|afternoon|evening)|sup|what(?:'s| is) up)\b[\s!.?]*$",
    re.I,
)
_CAPABILITY = re.compile(
    r"^(?:help|what can you do|capabilities|who are you|what are you)\b",
    re.I,
)

CAPABILITY_REPLY = """I'm the **PITER Ops** incident assistant. I can help you with:

- **Triage** — classify priority and summarize alert context
- **Runbooks** — grounded answers from the knowledge base
- **Deployments** — recent changes for a service
- **Escalation** — on-call paths and notification previews (human approval required)
- **Post-mortems** — draft summaries from investigation history

Select an incident context or ask one of the suggested questions to get started."""


def small_talk_reply(question: str) -> str | None:
    """Return a canned reply for greetings/capability asks, or None to continue RAG."""
    q = question.strip()
    if not q:
        return None
    if _GREETING.match(q):
        return CAPABILITY_REPLY
    if _CAPABILITY.match(q):
        return CAPABILITY_REPLY
    return None


def structured_chat_reply(question: str) -> dict[str, Any] | None:
    """Guardrail refusals and grounded demo answers before RAG/Bedrock."""
    guard = destructive_action_reply(question)
    if guard:
        return guard
    return demo_ops_reply(question)
