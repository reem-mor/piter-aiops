"""Integration tests for structured incident analysis (data/source + KB)."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.alert_stream import p1_demo_alert
from app.services.incident_analysis import analyze_incident, compose_piter_sections

ROOT = Path(__file__).resolve().parents[1]
KB_RUNBOOKS = ROOT / "knowledge_base" / "runbooks"


@pytest.fixture
def storm_alert() -> dict:
    alert = p1_demo_alert()
    alert.setdefault("duration_minutes", 45)
    return alert


def test_priority_raises_p3_to_p2_on_revenue():
    from app.services.incident_analysis import _classify_priority

    alert = {"severity": "P3", "error_rate_pct": 1.0, "service": "auth-service"}
    impact = {"cost_per_minute": 2000, "regulatory_exposure": []}
    priority = _classify_priority(alert=alert, impact=impact, source_dir=None)
    assert priority["priority"] == "P2"


def test_bet_service_gib_ukgc_p1_full_flow(storm_alert: dict):
    analysis = analyze_incident(storm_alert)
    assert "error" not in analysis

    owner = analysis["owner"]
    assert owner["owner_team"] == "Betting Core"

    deploys = analysis["deployments"]
    assert deploys.get("likely_deploy_correlation") is True
    assert any(d["service"] == "bet-service" for d in deploys.get("deployments", []))

    impact = analysis["impact"]
    assert impact.get("cost_per_minute") == pytest.approx(9800, rel=0.01)
    assert impact.get("active_users") == pytest.approx(32000, rel=0.01)
    regulatory = " ".join(impact.get("regulatory_exposure", [])).upper()
    assert "UKGC" in regulatory

    priority = analysis["priority"]
    assert priority["priority"] == "P1"
    assert priority.get("rationale")

    escalation = analysis["escalation"]
    assert escalation.get("war_room_required") is True
    reg = escalation.get("regulatory_override") or {}
    assert "UKGC" in str(reg.get("regulator", "")).upper() or reg.get("notify_within_minutes")

    similar = analysis["similar_incidents"].get("similar_incidents", [])
    assert any(
        inc.get("incident_id") == "INC-2025-11-04-GIB-BET-OUTAGE" for inc in similar
    )

    kb = analysis["knowledge_base"]
    assert kb.get("found") is True
    assert kb.get("runbook_file") == "deployment_rollback.json"

    sections = compose_piter_sections(analysis)
    piter = sections.get("piter_sections") or {}
    assert piter.get("triage_plan")

    sources = analysis.get("sources", [])
    assert any("deployment_rollback.json" in str(s) for s in sources)
