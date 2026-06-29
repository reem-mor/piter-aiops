"""Spec-aligned tests for the four enrichment tools (happy path + edge cases).

All tools read EXCLUSIVELY from the canonical data/source/ datasets. The demo
scenario is the P1 storm trigger: bet-service in GIB-UKGC.
"""
from __future__ import annotations

from app.enrichment_tools import (
    correlate_deployments,
    find_similar_incidents,
    lookup_owner_and_escalation,
    score_business_impact,
)

ALERT_TIME = "2026-06-10T10:02:55Z"


# --- Tool 1: correlate_deployments ---------------------------------------

def test_correlate_happy_path_has_suspect_and_reason():
    r = correlate_deployments(service="bet-service", environment="GIB-UKGC", alert_time=ALERT_TIME)
    assert r["likely_deploy_correlation"] is True
    assert r["suspect_deployment"]["service"] == "bet-service"
    assert "dependency_hop_explanation" in r
    assert r["reason"]


def test_correlate_window_minutes_narrows_lookback():
    r = correlate_deployments(
        service="bet-service", environment="GIB-UKGC", alert_time=ALERT_TIME,
        window_minutes=30,
    )
    assert r["window_minutes"] == 30
    # 30-min window collapses to a 1-hour lookback; the 09:55 deploy still lands.
    assert r["lookback_hours"] == 1


def test_correlate_unknown_service():
    r = correlate_deployments(service="nope", environment="GIB-UKGC", alert_time=ALERT_TIME)
    assert "error" in r and r["likely_deploy_correlation"] is False


def test_correlate_invalid_timestamp():
    r = correlate_deployments(service="bet-service", environment="GIB-UKGC", alert_time="not-a-time")
    assert "error" in r


def test_correlate_missing_environment():
    r = correlate_deployments(service="bet-service", environment="", alert_time=ALERT_TIME)
    assert "error" in r


# --- Tool 2: lookup_owner_and_escalation ---------------------------------

def test_owner_happy_path():
    r = lookup_owner_and_escalation(service="bet-service", severity="P1")
    assert r["owner_team"] == "Betting Core"
    assert r["primary_on_call"] == "Primary Betting Core On-Call"
    assert r["slack_channel"] == "#betting-core"
    assert r["escalation_chain"][0] == "Primary Betting Core On-Call"
    assert "depends_on" in r["dependencies"]


def test_owner_unknown_service():
    assert "error" in lookup_owner_and_escalation(service="ghost")


def test_owner_missing_service():
    assert "error" in lookup_owner_and_escalation(service="")


# --- Tool 3: score_business_impact ---------------------------------------

def test_impact_happy_path_costs():
    r = score_business_impact(
        service="bet-service", environment="GIB-UKGC", severity="P1",
        duration_minutes=60, alert={"error_rate_pct": 100},
    )
    assert r["revenue_impact_usd_per_hour"] == 588000
    assert r["cost_per_15min"] == 147000
    assert r["estimated_total_cost"] == 588000
    assert r["sla_risk"] == "critical"
    assert r["regulatory_flag"] is True
    assert r["fallback"] is False


def test_impact_duration_scales_total():
    r = score_business_impact(
        service="bet-service", environment="GIB-UKGC", severity="P1", duration_minutes=30,
    )
    assert r["estimated_total_cost"] == 294000


def test_impact_unknown_service_errors():
    r = score_business_impact(service="ghost", environment="GIB-UKGC", severity="P1")
    assert "error" in r


def test_impact_invalid_duration_defaults():
    r = score_business_impact(
        service="bet-service", environment="GIB-UKGC", severity="P1", duration_minutes="oops",
    )
    assert r["duration_minutes"] == 60


# --- Tool 4: find_similar_incidents --------------------------------------

def test_similar_happy_path_has_resolution_and_reason():
    r = find_similar_incidents(
        service="bet-service", symptom="100% error rate nodes unresponsive outage",
        environment="GIB-UKGC", top_k=3,
    )
    assert r["count"] >= 1
    top = r["similar_incidents"][0]
    assert top["resolution"]
    assert top["similarity_reason"]
    assert top["environment"] == "GIB-UKGC"


def test_similar_top_k_limits():
    r = find_similar_incidents(service="bet-service", symptom="outage 100% error rate", top_k=1)
    assert r["count"] <= 1


def test_similar_no_match_for_unknown_service():
    r = find_similar_incidents(service="ghost-svc", symptom="cpu", top_k=3)
    assert r["count"] == 0
