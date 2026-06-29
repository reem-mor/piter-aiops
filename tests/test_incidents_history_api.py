"""Persisted incident history API."""

from app.services import session_memory


def test_incidents_history_empty(client):
    session_memory.reset()
    response = client.get("/api/incidents/history")
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["investigations"] == []
    assert data["count"] == 0


def test_incidents_history_lists_session(client):
    session_memory.reset()
    sid = session_memory.create_session(
        {
            "alert_id": "ALT-DEMO-1",
            "service": "bet-service",
            "environment": "GIB-UKGC",
            "severity": "P1",
            "symptom": "High error rate",
            "alert_time": "2026-06-10T12:00:00Z",
        }
    )
    session_memory.save_triage(
        sid,
        citations=[],
        tool_outputs={},
        triage_card={
            "priority": "P1",
            "service": "bet-service",
            "mode": "local_fallback",
            "fallback_used": True,
        },
    )

    response = client.get("/api/incidents/history")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    row = data["investigations"][0]
    assert row["session_id"] == sid
    assert row["service"] == "bet-service"
    assert row["severity"] == "P1"


def test_incident_history_detail(client):
    session_memory.reset()
    sid = session_memory.create_session({"alert_id": "ALT-2", "service": "wallet-service"})
    session_memory.save_triage(sid, citations=[], tool_outputs={}, triage_card={"summary": "test"})

    response = client.get(f"/api/incidents/history/{sid}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["session_id"] == sid
    assert data["triage_card"]["summary"] == "test"


def test_incident_history_detail_missing(client):
    session_memory.reset()
    response = client.get("/api/incidents/history/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["reason"] == "unknown_session"
