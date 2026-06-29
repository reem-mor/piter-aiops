"""Escalation recommendation tool for PITER AiOps."""
from __future__ import annotations

from typing import Any

from app.enrichment_tools import lookup_owner_and_escalation


def get_escalation_recommendation(
    service: str,
    priority: str = "P2",
    business_impact: str = "",
) -> dict[str, Any]:
    """Return a safe escalation recommendation. Never sends notifications."""
    if not service or not service.strip():
        return {"error": "Missing service", "sends_notifications": False}
    owner = lookup_owner_and_escalation(service=service.strip(), severity=priority)
    if owner.get("error"):
        return {**owner, "sends_notifications": False}
    return {
        "service": owner.get("service", service),
        "priority": priority.upper(),
        "business_impact": business_impact,
        "escalation_target": owner.get("primary_on_call"),
        "secondary_escalation": owner.get("secondary_escalation"),
        "channel": owner.get("slack_channel"),
        "safe_preview_only": True,
        "sends_notifications": False,
        "message": (
            f"{priority.upper()} {service} incident. Impact: "
            f"{business_impact or 'impact not yet quantified'}. "
            "Human confirmation required before live notification."
        ),
    }
