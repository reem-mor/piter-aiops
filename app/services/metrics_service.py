"""HTTP handlers for /api/metrics/* enrichment endpoints."""
from __future__ import annotations

from typing import Any

from app.enrichment_tools import (
    correlate_deployments,
    find_similar_incidents,
    lookup_owner_and_escalation,
    score_business_impact,
)
from app.enrichment_tools import lookup_owner_and_escalation as _lookup_owner


def _safe_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def recent_deployments_metrics(
    *,
    service: str,
    environment: str,
    alert_time: str,
    lookback_hours: str | None = None,
) -> dict[str, Any]:
    if not service or not environment or not alert_time:
        return {"error": "service, environment, and alert_time are required"}
    return correlate_deployments(
        service=service.strip(),
        environment=environment.strip(),
        alert_time=alert_time.strip(),
        lookback_hours=_safe_int(lookback_hours, 6),
    )


def service_context_metrics(
    *,
    service: str,
    environment: str,
    severity: str | None = None,
) -> dict[str, Any]:
    if not service or not environment:
        return {"error": "service and environment are required"}
    owner = lookup_owner_and_escalation(
        service=service.strip(),
        environment=environment.strip(),
        severity=(severity or "").strip(),
    )
    if owner.get("error"):
        return owner
    owner["on_call_channel"] = owner.get("slack_channel", "")
    owner["escalation"] = owner.get("escalation_path", "")
    return owner


def similar_incidents_metrics(
    *,
    service: str,
    symptom: str,
    environment: str | None = None,
    limit: str | None = None,
) -> dict[str, Any]:
    if not service or not symptom:
        return {"error": "service and symptom are required"}
    return find_similar_incidents(
        service=service.strip(),
        symptom=symptom.strip(),
        environment=(environment or "").strip(),
        limit=_safe_int(limit, 5),
    )


def escalation_preview_metrics(
    *,
    service: str,
    severity: str | None = None,
    business_impact: str | None = None,
) -> dict[str, Any]:
    from app.services.escalation_service import resolve_demo_recipients

    if not service:
        return {"error": "service is required"}
    priority = (severity or "P2").strip().upper()
    owner = _lookup_owner(service=service.strip(), severity=priority)
    if owner.get("error"):
        return {**owner, "sends_notifications": False}
    impact = (business_impact or "").strip()
    recipients = resolve_demo_recipients("email")
    primary = recipients[0] if recipients else owner.get("primary_on_call")
    return {
        "service": owner.get("service", service),
        "priority": priority,
        "business_impact": impact,
        "escalation_target": owner.get("primary_on_call"),
        "secondary_escalation": owner.get("secondary_escalation"),
        "channel": owner.get("slack_channel"),
        "on_call_channel": owner.get("slack_channel", ""),
        "recipient": primary,
        "on_call_email": primary,
        "email_recipients": recipients,
        "safe_preview_only": True,
        "sends_notifications": False,
        "team": owner.get("owner_team") or owner.get("team") or "Platform On-Call",
        "escalation_team": owner.get("owner_team") or owner.get("team") or "Platform On-Call",
        "message": (
            f"{priority} {service} incident. Impact: "
            f"{impact or 'impact not yet quantified'}. "
            "Human confirmation required before live notification."
        ),
    }


def business_impact_metrics(
    *,
    service: str,
    environment: str,
    severity: str,
    duration_minutes: str | None = None,
) -> dict[str, Any]:
    if not all([service, environment, severity]):
        return {"error": "service, environment, and severity are required"}
    return score_business_impact(
        service=service.strip(),
        environment=environment.strip(),
        severity=severity.strip(),
        duration_minutes=_safe_int(duration_minutes, 60),
    )
