"""Bedrock agent service module smoke tests."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.services import bedrock_agent_service


def test_invoke_agent_delegates_to_client(fake_config, monkeypatch):
    mock_answer = MagicMock()
    mock_client = MagicMock()
    mock_client.ask.return_value = mock_answer

    monkeypatch.setattr(
        bedrock_agent_service,
        "get_agent_client",
        lambda config, client=None: mock_client,
    )

    result = bedrock_agent_service.invoke_agent(fake_config, "hello", session_id="s1")
    assert result is mock_answer
    mock_client.ask.assert_called_once()
