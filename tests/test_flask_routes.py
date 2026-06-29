"""Route tests for the local-first triage API and Bedrock auto-fallback."""
from __future__ import annotations

import pytest

from app import create_app
from app.bedrock_client import Citation, RagAnswer
from app.errors import BedrockError
from app.services import session_memory
from app.services.alert_stream import p1_demo_alert


@pytest.fixture(autouse=True)
def _clean_sessions():
    session_memory.reset()
    yield
    session_memory.reset()


# --- /health, /api/demo-alert ----------------------------------------------

def test_health_ok(local_client):
    resp = local_client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_demo_alert(local_client):
    resp = local_client.get("/api/demo-alert")
    body = resp.get_json()
    assert body["ok"] is True
    assert body["alert"]["service"] == "bet-service"
    assert body["alert"]["environment"] == "GIB-UKGC"


# --- /api/triage -----------------------------------------------------------

def test_triage_returns_card(local_client):
    alert = local_client.get("/api/demo-alert").get_json()["alert"]
    resp = local_client.post("/api/triage", json=alert)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["mode"] == "local"
    assert body["grounded"] is True
    assert any(c["document"] == "deployment_rollback.json" for c in body["citations"])
    for key in ("recommended_steps", "owner", "impact", "similar_incidents", "session_id"):
        assert key in body


def test_triage_bet_service_storm_returns_piter_sections(local_client):
    alert = p1_demo_alert()
    resp = local_client.post("/api/triage", json=alert)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["owner"]["owner_team"] == "Betting Core"
    assert body["impact"]["revenue_impact_usd_per_hour"] == 588000
    assert body.get("piter_sections")
    assert body["piter_sections"].get("triage_plan")
    assert body.get("priority_rationale")
    assert body.get("escalation_policy")
    assert body["similar_incidents"]


def test_triage_rejects_incomplete_alert(local_client):
    resp = local_client.post("/api/triage", json={"environment": "NJ-DGE"})
    assert resp.status_code == 400
    assert resp.get_json()["reason"] == "invalid_alert"


# --- /api/follow-up --------------------------------------------------------

def test_follow_up_reuses_session(local_client):
    alert = local_client.get("/api/demo-alert").get_json()["alert"]
    sid = local_client.post("/api/triage", json=alert).get_json()["session_id"]
    resp = local_client.post("/api/follow-up", json={"session_id": sid, "question": "who do I escalate to?"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["memory_used"] is True
    assert "Primary Betting Core On-Call" in body["answer"]


def test_follow_up_missing_session(local_client):
    resp = local_client.post("/api/follow-up", json={"question": "hello there"})
    assert resp.status_code == 400
    assert resp.get_json()["reason"] == "missing_session"


def test_follow_up_unknown_session_falls_back_to_rag(local_client):
    resp = local_client.post(
        "/api/follow-up",
        json={"session_id": "nope", "question": "What should I check when users cannot log in after deployment?"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body.get("memory_used") is False
    assert body.get("answer")


def test_chat_with_chat_only_session_id_uses_rag(local_client):
    resp = local_client.post(
        "/api/chat",
        json={
            "session_id": "demo-default",
            "message": "What should I check when users cannot log in after deployment?",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body.get("answer")


def test_console_legacy_archived_when_spa_disabled(local_client):
    """FORCE_LEGACY_UI disables SPA; archived console returns spa_not_built."""
    resp = local_client.get("/console")
    assert resp.status_code == 503
    body = resp.get_json()
    assert body["reason"] == "spa_not_built"


# --- Bedrock auto-fallback to local ----------------------------------------

class _FailingClient:
    def ask(self, question, *, session_id=None, session_attributes=None, prompt_session_attributes=None):
        raise BedrockError("Bedrock is down", code="bedrock_error")


def test_ask_falls_back_to_local(fake_config):
    app = create_app(fake_config)
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, FORCE_LEGACY_UI=True, LOCAL_FALLBACK=True)
    app.extensions["bedrock_client"] = _FailingClient()
    client = app.test_client()
    resp = client.post("/api/chat", json={"message": "Postgres CPU is 95% on prod-db-1 — what is the runbook?"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["mode"] == "local_fallback"
    assert body["citations"][0]["source_label"] == "database_connectivity.json"


def test_triage_uses_direct_kb_client(client, fake_bedrock):
    fake_bedrock.next_response = RagAnswer(
        answer="Priority:\nP2\n\nTriage plan:\n1. Check deploy logs.",
        citations=[
            Citation(
                snippet="Roll back if deploy correlated.",
                source_uri="s3://bucket/knowledge_base/runbooks/deployment_rollback.json",
                source_label="deployment_rollback.json",
            )
        ],
        session_id="kb-sess-1",
        grounded=True,
        mode="bedrock",
    )
    client.application.extensions["triage_client"] = fake_bedrock
    alert = {
        "alert_id": "ALT-TEST-1",
        "service": "bet-service",
        "environment": "GIB-UKGC",
        "severity": "P1",
        "symptom": "100% error rate",
        "alert_time": "2026-06-10T10:02:00Z",
    }
    resp = client.post("/api/triage", json=alert)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert len(fake_bedrock.calls) == 1
    assert "100% error rate" in fake_bedrock.calls[0]
    assert fake_bedrock.last_session_attributes is None
    assert body.get("citations")
    assert body.get("piter_sections") or body.get("piter")
    assert body["mode"] == "bedrock"


def test_validation_error_not_masked_by_fallback(fake_config):
    app = create_app(fake_config)
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, FORCE_LEGACY_UI=True, LOCAL_FALLBACK=True)
    app.extensions["bedrock_client"] = _FailingClient()
    client = app.test_client()
    resp = client.post("/api/chat", json={"message": "x"})
    assert resp.status_code == 400  # short_question, not a fallback
