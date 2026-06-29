"""Session memory and chat history API tests."""
from __future__ import annotations


def test_api_history_get_default(client):
    response = client.get("/api/history")
    assert response.status_code == 200
    body = response.get_json()
    assert body.get("ok") is True
    assert "messages" in body


def test_api_history_clear(local_client):
    local_client.post(
        "/api/chat",
        json={"message": "Summarize escalation policy for P1 incidents"},
    )
    response = local_client.delete("/api/history", json={})
    assert response.status_code == 200
    body = response.get_json()
    assert body.get("ok") is True
