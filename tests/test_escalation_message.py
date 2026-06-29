"""Tests for escalation message formatting."""
from __future__ import annotations

from app.services.escalation_message import enrich_escalation_context, format_escalation_messages


def test_format_escalation_email_includes_on_call_and_war_room():
    ctx = {
        "incident_id": "ALT-DEMO-P1-001",
        "severity": "P1",
        "service": "auth-service",
        "environment": "GIB-UKGC",
        "incident_title": "Login failure after deployment",
        "on_call_name": "Roy Katz",
        "owner_team": "Identity & Access",
        "slack_channel": "#identity",
        "war_room_channel": "#war-room",
        "business_impact": "Complete login outage for regulated market users.",
        "support_complaints": "47 CS tickets (+35% vs baseline).",
        "top_error": "jwt_validation_failed +280%",
        "recent_deployment": "v2.4.1 (27m ago)",
        "recommended_actions": ["Rollback auth-api canary", "Validate JWT signing keys"],
        "runbook_count": 5,
        "runbook_name": "auth_service_login_failure.md",
    }
    formatted = format_escalation_messages(ctx, channel="email")
    body = formatted["body"]
    assert "Hey Roy Katz" in body
    assert "#war-room" in body
    assert "jwt_validation_failed +280%" in body
    assert "Business impact" in body or "BUSINESS IMPACT" in body
    assert formatted["html_body"]
    assert "Login failure after deployment" in formatted["subject"]


def test_format_escalation_sms_is_concise():
    ctx = {
        "incident_id": "INC-1",
        "severity": "P1",
        "service": "bet-service",
        "incident_title": "100% error rate",
        "on_call_name": "Tom Friedman",
        "business_impact": "$520k/hr exposure",
        "top_error": "HTTP 5xx spike",
        "war_room_channel": "#war-room",
    }
    sms = format_escalation_messages(ctx, channel="sms")["body"]
    assert "Tom Friedman" in sms
    assert "war-room" in sms
    assert "@" not in sms
    assert len(sms) <= 160


def test_enrich_escalation_context_fills_owner_from_catalog():
    ctx = enrich_escalation_context(
        {"incident_title": "P1 bet outage"},
        incident_id="ALT-1",
        service="bet-service",
        severity="P1",
    )
    assert ctx["on_call_name"]
    assert ctx["owner_team"]
    assert ctx.get("business_impact")
