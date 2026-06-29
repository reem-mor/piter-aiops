"""Bedrock Agent service — production invoke path for chat and triage."""
from __future__ import annotations

from typing import Any

from app.bedrock_agent_client import BedrockAgentClient, build_session_attributes
from app.bedrock_client import RagAnswer
from app.config import Config


def get_agent_client(
    config: Config,
    *,
    client: object | None = None,
) -> BedrockAgentClient:
    """Return a configured Bedrock Agent runtime client."""
    return BedrockAgentClient(config, client=client)


def invoke_agent(
    config: Config,
    question: str,
    *,
    session_id: str | None = None,
    session_attributes: dict[str, str] | None = None,
    prompt_session_attributes: dict[str, str] | None = None,
    client: object | None = None,
) -> RagAnswer:
    """Invoke the Bedrock Agent with optional session memory attributes."""
    agent = get_agent_client(config, client=client)
    return agent.ask(
        question,
        session_id=session_id,
        session_attributes=session_attributes,
        prompt_session_attributes=prompt_session_attributes,
    )


def invoke_agent_for_alert(
    config: Config,
    question: str,
    alert: dict[str, Any],
    *,
    session_id: str | None = None,
    triage_complete: str = "false",
    client: object | None = None,
) -> RagAnswer:
    """Invoke the agent with alert-scoped session attributes."""
    session_attrs, prompt_attrs = build_session_attributes(
        alert_id=str(alert.get("alert_id") or ""),
        service=str(alert.get("service") or ""),
        environment=str(alert.get("environment") or ""),
        severity=str(alert.get("severity") or ""),
        symptom=str(alert.get("symptom") or alert.get("description") or ""),
        alert_time=str(alert.get("alert_time") or ""),
        triage_complete=triage_complete,
    )
    return invoke_agent(
        config,
        question,
        session_id=session_id,
        session_attributes=session_attrs,
        prompt_session_attributes=prompt_attrs,
        client=client,
    )
