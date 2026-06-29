"""Tests for /api/metrics/* enrichment endpoints."""
from __future__ import annotations


def test_metrics_recent_deployments_requires_params(client):
    response = client.get("/api/metrics/recent-deployments")
    assert response.status_code == 400
    body = response.get_json()
    assert body.get("error")


def test_metrics_recent_deployments_auth_service(client):
    response = client.get(
        "/api/metrics/recent-deployments",
        query_string={
            "service": "auth-service",
            "environment": "MGM",
            "alert_time": "2026-06-10T09:00:00Z",
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body.get("ok") is True
    assert "deployments" in body


def test_metrics_service_context(client):
    response = client.get(
        "/api/metrics/service-context",
        query_string={"service": "bet-service", "environment": "GIB-UKGC"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body.get("owner_team")
    assert "on_call_channel" in body


def test_metrics_similar_incidents(client):
    response = client.get(
        "/api/metrics/similar-incidents",
        query_string={
            "service": "auth-service",
            "symptom": "login failure spike after deployment",
        },
    )
    assert response.status_code == 200
    assert response.get_json().get("similar_incidents") is not None


def test_metrics_business_impact(client):
    response = client.get(
        "/api/metrics/business-impact",
        query_string={
            "service": "auth-service",
            "environment": "MGM",
            "severity": "P1",
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body.get("ok") is True
    assert body.get("business_explanation") or body.get("revenue_impact_usd_per_hour") is not None


def test_metrics_escalation_preview_never_sends(client):
    response = client.get(
        "/api/metrics/escalation-preview",
        query_string={"service": "bet-service", "severity": "P1"},
    )
    body = response.get_json()
    assert response.status_code == 200
    assert body.get("safe_preview_only") is True
    assert body.get("sends_notifications") is False


def test_api_investigations_from_alert_stream(client):
    response = client.get("/api/investigations")
    assert response.status_code == 200
    body = response.get_json()
    assert body.get("ok") is True
    invs = body.get("investigations") or []
    assert len(invs) >= 1
    assert invs[0].get("service")


def test_api_incident_analyze_alias(local_client):
    response = local_client.post(
        "/api/incident/analyze",
        json={
            "service": "auth-service",
            "environment": "MGM",
            "severity": "P2",
            "symptom": "Users cannot log in after deployment",
            "alert_time": "2026-06-10T08:30:00Z",
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body.get("ok") is True
    assert body.get("priority")
