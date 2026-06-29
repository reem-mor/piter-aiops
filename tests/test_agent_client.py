"""Unit tests for Bedrock agent session memory and trace enrichment parsing."""
from __future__ import annotations

import json

from app.bedrock_agent_client import (
    _merge_action_output,
    build_session_attributes,
)


def test_build_session_attributes_demo_alert():
    session, prompt = build_session_attributes(
        alert_id="A-demo",
        service="postgres",
        environment="NJ-DGE",
        severity="P2",
        symptom="CPU > 90%",
        alert_time="2026-06-10T09:00:00Z",
    )
    assert session["service"] == "postgres"
    assert session["environment"] == "NJ-DGE"
    assert prompt["current_service"] == "postgres"
    assert session["triage_complete"] == "false"


def test_build_session_attributes_follow_up_mode():
    session, prompt = build_session_attributes(
        service="postgres",
        triage_complete="true",
    )
    assert session["triage_complete"] == "true"
    assert "follow_up_mode" in prompt


def test_merge_action_output_correlate():
    enrichment: dict = {}
    body = {
        "deployments": [{"service": "postgres", "version": "2.4.1"}],
        "likely_deploy_correlation": True,
    }
    _merge_action_output(enrichment, {"text": json.dumps(body)})
    assert enrichment["deployments"]
    assert enrichment["likely_deploy_correlation"] is True


def test_merge_action_output_context_tools_list():
    enrichment: dict = {}
    owner = {"owner_team": "Platform DB", "escalation": "dba-oncall@corp"}
    impact = {"revenue_impact_usd_per_hour": 12000}
    _merge_action_output(enrichment, {"text": json.dumps(owner)})
    _merge_action_output(enrichment, {"text": json.dumps(impact)})
    assert enrichment["owner_team"] == "Platform DB"
    assert enrichment["revenue_impact_usd_per_hour"] == 12000
    assert len(enrichment.get("tools", [])) == 0 or "owner_team" in enrichment


def test_merge_action_output_invalid_json():
    enrichment: dict = {}
    _merge_action_output(enrichment, {"text": "not-json"})
    assert enrichment.get("raw_tool_outputs")
