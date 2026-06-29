"""Shared workflow triage result shaping for HTML and JSON responses."""
from __future__ import annotations

from typing import Any

from app.bedrock_client import RagAnswer
from app.text_utils import parse_action_bullets
from app.workflow_impact import severity_impact


def build_workflow_payload(
    *,
    result: RagAnswer,
    alert: dict[str, Any] | None,
    question: str,
    model_label: str,
) -> dict[str, Any]:
    actions = parse_action_bullets(result.answer)
    if not actions and alert:
        fallback = alert.get("actions")
        if isinstance(fallback, list):
            actions = [str(a) for a in fallback if str(a).strip()]

    effective_decision = alert.get("decision") if alert else None
    effective_reason = alert.get("decision_reason") if alert else None
    if not result.grounded:
        effective_decision = "escalate"
        effective_reason = "Insufficient knowledge-base context — escalate with prepared notes."

    matched_runbook = result.matched_runbook
    if not matched_runbook and result.citations:
        matched_runbook = result.citations[0].source_label
    if not matched_runbook and alert:
        matched_runbook = alert.get("matched_runbook")

    saved_min = 0
    impact_avoided = 0
    if alert:
        saved_min, impact_avoided = severity_impact(str(alert.get("severity", "P3")))

    enrichment = result.enrichment if getattr(result, "enrichment", None) else None
    owner_team = None
    similar = None
    if enrichment:
        owner_team = enrichment.get("owner_team")
        similar = enrichment.get("similar_incidents")
        if not owner_team and enrichment.get("tools"):
            for tool in enrichment["tools"]:
                if isinstance(tool, dict) and tool.get("owner_team"):
                    owner_team = tool["owner_team"]
                    break

    return {
        "result": result.to_dict(),
        "alert": alert,
        "question": question,
        "actions": actions,
        "matched_runbook": matched_runbook,
        "effective_decision": effective_decision,
        "effective_reason": effective_reason,
        "saved_min": saved_min,
        "impact_avoided": impact_avoided,
        "model_label": model_label,
        "enrichment": enrichment,
        "owner_team": owner_team,
        "similar_incidents": similar,
    }
