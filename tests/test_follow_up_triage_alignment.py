"""Follow-up answers must match the active triage card (session source of truth)."""
from __future__ import annotations

import pytest

from app.services.alert_stream import p1_demo_alert
from app.services import session_memory


@pytest.fixture(autouse=True)
def _clean_sessions():
    session_memory.reset()
    yield
    session_memory.reset()


def _storm_triage(local_client):
    alert = p1_demo_alert()
    triage = local_client.post("/api/triage", json=alert).get_json()
    assert triage["ok"] is True
    return triage


def test_storm_p1_triage_card(local_client):
    triage = _storm_triage(local_client)
    assert triage["owner"]["owner_team"] == "Betting Core"
    assert triage["impact"]["revenue_impact_usd_per_hour"] == 588000
    assert triage.get("suspect_deploys")


def test_follow_up_escalation_matches_triage_card(local_client):
    triage = _storm_triage(local_client)
    sid = triage["session_id"]
    follow = local_client.post(
        "/api/follow-up",
        json={"session_id": sid, "question": "Who should I escalate this to?"},
    ).get_json()
    assert follow["ok"] is True
    assert follow["session_id"] == sid
    assert follow["memory_used"] is True
    assert "Betting Core" in follow["answer"]
    primary = triage["owner"].get("primary_on_call") or triage["owner"].get("primary_on_call_role", "")
    assert primary in follow["answer"]

    history = local_client.get(f"/api/sessions/{sid}/history").get_json()
    assert history["ok"] is True
    assert history["session_id"] == sid
    assert history["triage_summary"]["priority"] == triage["priority"]
    assert len(history["followups"]) == 1
    assert history["followups"][0]["question"] == "Who should I escalate this to?"
    assert history["followups"][0]["answer"]["memory_used"] is True


def test_follow_up_deployment_matches_triage_card(local_client):
    triage = _storm_triage(local_client)
    sid = triage["session_id"]
    follow = local_client.post(
        "/api/follow-up",
        json={"session_id": sid, "question": "Was there a recent deployment?"},
    ).get_json()
    assert follow["ok"] is True
    assert follow["session_id"] == sid
    suspect = triage.get("suspect_deployment") or {}
    if suspect:
        assert suspect.get("service", "bet-service") in follow["answer"]
        assert suspect.get("version", "") in follow["answer"] or "bet-service" in follow["answer"]
    else:
        assert follow["answer"] == triage.get("deployment_reason", follow["answer"])


def test_follow_up_business_impact_matches_triage_card(local_client):
    triage = _storm_triage(local_client)
    sid = triage["session_id"]
    follow = local_client.post(
        "/api/follow-up",
        json={"session_id": sid, "question": "What is the business impact?"},
    ).get_json()
    assert follow["ok"] is True
    assert follow["session_id"] == sid
    card_impact = triage["impact"].get("business_explanation", "")
    assert card_impact
    assert follow["answer"] == card_impact
    assert str(triage["impact"]["revenue_impact_usd_per_hour"]) in follow["answer"] or "588" in follow["answer"]


def test_session_history_unknown_session_returns_404(local_client):
    response = local_client.get("/api/sessions/not-a-session/history")
    assert response.status_code == 404
    data = response.get_json()
    assert data["ok"] is False
    assert data["reason"] == "unknown_session"
