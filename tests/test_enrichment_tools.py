"""Unit tests for enrichment tools (canonical data/source/ scenarios)."""
from __future__ import annotations

from pathlib import Path

from app.enrichment_tools import (
    correlate_deployments,
    enrich_triage_demo,
    find_similar_incidents,
    lookup_owner,
    score_business_impact,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "source"

DEMO = {
    "service": "auth-service",
    "environment": "NJ-DGE",
    "severity": "P2",
    "symptom": "login failures and token validation errors",
    "alert_time": "2026-06-10T10:40:00Z",
}


def test_correlate_deployments_demo():
    result = correlate_deployments(
        service=DEMO["service"],
        environment=DEMO["environment"],
        alert_time=DEMO["alert_time"],
    )
    assert "error" not in result
    assert result["environment"] == "NJ-DGE"
    assert "deployments" in result


def test_lookup_owner_demo():
    result = lookup_owner(service=DEMO["service"], environment=DEMO["environment"])
    assert result["owner_team"] == "Identity & Access"
    assert "Identity & Access" in result["escalation_path"] or result["escalation_path"]


def test_score_business_impact_demo():
    result = score_business_impact(
        service=DEMO["service"],
        environment=DEMO["environment"],
        severity=DEMO["severity"],
    )
    assert result["revenue_impact_usd_per_hour"] > 0
    assert "regulatory_flag" in result


def test_find_similar_incidents_demo():
    result = find_similar_incidents(service="bet-service", symptom="100% error rate outage")
    assert result["count"] >= 1


def test_enrich_triage_demo_bundle():
    bundle = enrich_triage_demo()
    assert bundle["correlate_deployments"]["likely_deploy_correlation"] is True
    assert bundle["lookup_owner"]["owner_team"] == "Betting Core"
    assert bundle["score_business_impact"]["tier"] == 0
    assert bundle["find_similar_incidents"]["count"] >= 1


STORM = {
    "service": "bet-service",
    "environment": "GIB-UKGC",
    "severity": "P1",
    "symptom": "CRITICAL: bet-service nodes unresponsive — 100% error rate on GIB-UKGC",
    "alert_time": "2026-06-10T10:02:55Z",
}


def test_bet_service_storm_enrichment():
    owner = lookup_owner(
        service=STORM["service"],
        environment=STORM["environment"],
        data_dir=SOURCE_DIR,
    )
    assert "error" not in owner
    assert owner["owner_team"] == "Betting Core"

    deploys = correlate_deployments(
        service=STORM["service"],
        environment=STORM["environment"],
        alert_time=STORM["alert_time"],
        data_dir=SOURCE_DIR,
    )
    assert "error" not in deploys
    assert deploys["likely_deploy_correlation"] is True

    impact = score_business_impact(
        service=STORM["service"],
        environment=STORM["environment"],
        severity=STORM["severity"],
        alert=STORM,
        data_dir=SOURCE_DIR,
    )
    assert impact["sla_risk"] == "critical"
    assert impact["revenue_impact_usd_per_hour"] == 588000

    similar = find_similar_incidents(
        service=STORM["service"],
        symptom=STORM["symptom"],
        environment=STORM["environment"],
        data_dir=SOURCE_DIR,
    )
    assert similar["count"] >= 1
