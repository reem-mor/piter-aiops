"""Tests for answer/citation formatting helpers."""
from __future__ import annotations

import json

from app.text_utils import (
    extract_reference_metadata,
    format_answer_sections,
    format_citation_preview,
)


def test_format_answer_sections_parses_headings():
    raw = """Summary:
Postgres CPU is elevated on prod-db-1.

Recommended steps:
1. Check pg_stat_activity for long queries.
2. Cancel queries running longer than 5 minutes.

Escalation:
- Page DBA on-call if CPU stays above 90% for 15 minutes.

Why this answer:
Based on database_connectivity.md."""
    sections = format_answer_sections(raw)
    assert "Postgres CPU" in sections["summary"]
    assert len(sections["steps"]) >= 2
    assert sections["steps"][0].startswith("Check pg_stat_activity")
    assert any("DBA" in item for item in sections["escalation"])
    assert "database_connectivity" in sections["why"]


def test_format_answer_sections_derives_steps_from_plain_text():
    raw = "1. Roll back the last deploy.\n2. Check error logs."
    sections = format_answer_sections(raw)
    assert len(sections["steps"]) == 2
    assert sections["steps"][0].startswith("Roll back")


def test_format_citation_preview_parses_json_alert():
    alert = {
        "id": "A-1042",
        "severity": "P1",
        "title": "Checkout 5xx spike",
        "fired": "2024-07-12T14:00:00Z",
        "resolved_after_min": 47,
    }
    preview = format_citation_preview(json.dumps(alert), "alerts_last_3mo.json")
    assert "A-1042" in preview
    assert "P1" in preview
    assert "Checkout" in preview
    assert "[" not in preview[:80]


def test_format_citation_preview_markdown_heading():
    snippet = "# Database CPU runbook\n\nCheck pg_stat_activity first."
    preview = format_citation_preview(snippet, "database_connectivity.md")
    assert "Database CPU" in preview
    assert "pg_stat_activity" in preview


def test_format_answer_sections_inline_numbered_and_escalation():
    raw = (
        "1. Check worker count on checkout-service. 2. Inspect dead-letter queue depth. "
        "3. Scale workers if lag persists. Escalation: Page payments on-call if DLQ > 1000 "
        "for 10 minutes. Why this answer: Based on runbook_queue_lag.md."
    )
    sections = format_answer_sections(raw)
    assert len(sections["steps"]) == 3
    assert "worker count" in sections["steps"][0]
    assert "dead-letter" in sections["steps"][1]
    assert any("payments" in item.lower() for item in sections["escalation"])
    assert "runbook_queue_lag" in sections["why"]


def test_format_answer_sections_parses_piter_headings():
    raw = """Priority:
P2 — Postgres CPU elevated on prod-db-1; revenue path indirectly affected.

Investigation findings:
Long-running queries detected; replica lag within SLO.

Triage plan:
1. Check pg_stat_activity for long queries.
2. Cancel queries running longer than 5 minutes.

Escalation recommendation:
Page DBA on-call if CPU stays above 90% for 15 minutes.

Resolution plan:
Verify CPU normalizes after query cancellation; document in incident ticket.

Business impact:
Checkout latency risk if DB remains saturated.

Sources:
database_connectivity.md

Confidence and uncertainty:
High confidence — steps match runbook; uncertain if index rebuild needed."""
    sections = format_answer_sections(raw)
    assert sections.get("piter_sections") is not None
    piter = sections["piter_sections"]
    assert "P2" in piter["priority"]
    assert "Long-running" in piter["investigation"]
    assert any("pg_stat_activity" in step for step in piter["triage_plan"])
    assert len(piter["triage_plan"]) >= 2
    assert any("DBA" in item for item in piter["escalation"])
    assert "Postgres CPU" in sections["summary"] or "P2" in sections["summary"]
    assert len(sections["steps"]) >= 2


def test_extract_reference_metadata_score_and_chunk():
    ref = {
        "metadata": {"score": 0.87, "chunk_index": 3},
    }
    score, chunk = extract_reference_metadata(ref)
    assert score == 0.87
    assert chunk == 3
