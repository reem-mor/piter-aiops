"""Chat API contract tests (/api/chat)."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.bedrock_client import RagAnswer


def test_api_chat_empty_message(client):
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 400
    assert response.get_json().get("reason") == "empty_question"


def test_api_chat_success_local(local_client):
    response = local_client.post(
        "/api/chat",
        json={"message": "What is the triage plan for auth-service login failures?"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body.get("ok") is True
    assert body.get("answer")
    assert body.get("memory", {}).get("last_question")


def test_api_chat_success_mocked(client, monkeypatch):
    mock = MagicMock()
    mock.ask.return_value = RagAnswer(
        answer="Priority: P2\nInvestigation findings: test",
        citations=[],
        session_id="sess-chat-1",
        grounded=True,
        latency_ms=12,
        mode="bedrock",
    )
    monkeypatch.setattr("app.routes._client", lambda: mock)

    response = client.post(
        "/api/chat",
        json={"message": "What is the triage plan for auth-service login failures?"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body.get("ok") is True
    assert body.get("answer")
    assert body.get("memory", {}).get("last_question")
