"""Tests for structured analysis schema used by Analyze Alert UI."""
from __future__ import annotations

from app.services.structured_analysis import build_structured_analysis, strip_markdown


def test_strip_markdown_removes_bold():
    assert strip_markdown("**Priority: P1** — outage") == "Priority: P1 — outage"


def test_wallet_service_correlation_chain():
    payload = {
        "priority": "P1",
        "business_impact": "Replication lag after wallet-service deploy.",
        "alert": {
            "service": "wallet-service",
            "environment": "GIB-UKGC",
            "symptom": "Replication lag exceeded threshold",
            "alert_time": "2026-06-06T09:15:00Z",
        },
        "suspect_deployment": {
            "service": "wallet-service",
            "version": "v4.12.3",
            "deployed_at": "2026-06-06T08:30:00Z",
            "change_summary": "Connection pool tuning",
        },
        "similar_incidents": [
            {
                "incident_id": "INC-2025-04-12-WALLET-REP",
                "service": "wallet-service",
                "summary": "Replication lag after wallet-service deploy",
            }
        ],
        "recommended_steps": ["**Check replication lag**", "Validate wallet-service health"],
        "owner": {
            "owner_team": "Payments Core",
            "primary_oncall": "Payments On-Call",
            "escalation_path": "Primary → Secondary",
        },
        "requires_escalation": True,
        "matched_runbook": "deployment_rollback.json",
        "tool_results": [
            {"name": "get_recent_deployments", "result": {}},
            {"name": "find_similar_incidents", "result": []},
        ],
        "piter": {
            "priority": "P1",
            "investigation": "wallet-service replication lag correlated to v4.12.3 deploy.",
            "triage": "1. Check replication metrics\n2. Roll back if needed",
            "escalation": "Notify Payments On-Call",
            "resolution": "Rollback wallet-service",
        },
    }

    structured = build_structured_analysis(payload)
    assert structured["severity"] == "P1"
    assert "**" not in " ".join(structured["recommended_actions"])
    assert len(structured["correlation_chain"]) == 3
    assert structured["correlation_chain"][0]["step"] == "deployment"
    assert "v4.12.3" in structured["correlation_chain"][0]["label"]
    assert structured["correlation_chain"][1]["step"] == "alert"
    assert structured["correlation_chain"][2]["step"] == "similar_incident"
    assert structured["similar_incidents"][0]["incident_id"] == "INC-2025-04-12-WALLET-REP"
    assert structured["escalation_suggestion"]["owner_team"] == "Payments Core"
    assert structured["detected_pattern"]
    assert structured["log_enrichment"]
    assert "get_recent_deployments" in structured["tools_called"]


def test_evidence_caps_and_dedupes_summary():
    long_investigation = (
        "Wallet-service replication lag exceeded threshold after v4.12.3 deploy. "
        "Secondary platform failures observed in GIB-UKGC. "
        "Connection pool saturation correlated with deployment window. "
        "Historical pattern matches INC-2025-04-12-WALLET-REP."
    )
    payload = {
        "priority": "P1",
        "business_impact": "Replication lag after wallet-service deploy.",
        "alert": {"service": "wallet-service", "environment": "GIB-UKGC"},
        "matched_runbook": "deployment_rollback.json",
        "piter": {"investigation": long_investigation, "priority": "P1"},
    }
    structured = build_structured_analysis(payload)
    assert structured["summary"] == "Replication lag after wallet-service deploy."
    assert len(structured["evidence"]) <= 5
    for item in structured["evidence"]:
        assert len(item) <= 161
    assert not any(structured["summary"].lower() in e.lower() for e in structured["evidence"])


def test_recommended_actions_capped():
    payload = {
        "priority": "P2",
        "recommended_steps": [f"Step {i}: do something important" for i in range(1, 15)],
        "piter": {"priority": "P2"},
    }
    structured = build_structured_analysis(payload)
    assert len(structured["recommended_actions"]) <= 8
