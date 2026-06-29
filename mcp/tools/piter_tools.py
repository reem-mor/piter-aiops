"""PITER AiOps MCP tools — read-only adapters over app.enrichment_tools.

These four tools mirror the production Bedrock Action Groups (the four PITER
Lambdas) but run locally for the MCP demo/contract layer. They are READ-ONLY:
they never call AWS, never open the network, and never send notifications.

Single source of truth: every tool delegates to ``app.enrichment_tools`` so MCP,
the Flask app, and the AWS Lambdas all share identical behaviour and datasets.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

# Make the project importable when this server is launched directly.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app import enrichment_tools  # noqa: E402


def _mask_recipient(recipient: str) -> str:
    if not recipient:
        return ""
    if len(recipient) <= 4:
        return "*" * len(recipient)
    return f"{recipient[:2]}***{recipient[-2:]}"


def recent_deployments(arguments: dict[str, Any]) -> dict[str, Any]:
    return enrichment_tools.correlate_deployments(
        service=arguments["service"],
        environment=arguments["environment"],
        alert_time=arguments["alert_time"],
        lookback_hours=int(arguments.get("lookback_hours", 6)),
    )


def service_context(arguments: dict[str, Any]) -> dict[str, Any]:
    severity = str(arguments.get("severity", ""))
    owner = enrichment_tools.lookup_owner_and_escalation(
        service=arguments["service"], severity=severity
    )
    impact: dict[str, Any] = {}
    if arguments.get("environment") and severity:
        impact = enrichment_tools.score_business_impact(
            service=arguments["service"],
            environment=arguments["environment"],
            severity=severity,
            duration_minutes=int(arguments.get("duration_minutes", 60)),
        )
    return {"owner": owner, "impact": impact}


def similar_incidents(arguments: dict[str, Any]) -> dict[str, Any]:
    return enrichment_tools.find_similar_incidents(
        service=arguments["service"],
        symptom=arguments["symptom"],
        environment=str(arguments.get("environment", "")),
        limit=int(arguments.get("limit", 5)),
    )


def escalation_preview(arguments: dict[str, Any]) -> dict[str, Any]:
    """Read-only escalation preview. NEVER sends; recipients are masked.

    Live dispatch is intentionally unreachable from the MCP layer.
    """
    service = arguments["service"]
    severity = str(arguments.get("severity", ""))
    owner = enrichment_tools.lookup_owner_and_escalation(service=service, severity=severity)
    recipient = str(owner.get("primary_on_call") or "")
    return {
        "mode": "preview",
        "service": service,
        "severity": severity,
        "policy": "piter-standard-escalation",
        "escalation_chain": owner.get("escalation_chain"),
        "recipient_masked": _mask_recipient(recipient),
        "channels": ["sns", "ses"],
        "sends_notifications": False,
        "note": "MCP is read-only; live dispatch is only available via the gated Flask/Lambda path.",
    }


# name -> (handler, description, input JSON Schema)
TOOLS: dict[str, tuple[Callable[[dict[str, Any]], dict[str, Any]], str, dict[str, Any]]] = {
    "recent_deployments": (
        recent_deployments,
        "Correlate recent deployments for a service near an alert time (rollback availability).",
        {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "environment": {"type": "string"},
                "alert_time": {"type": "string", "description": "ISO-8601 timestamp"},
                "lookback_hours": {"type": "integer", "default": 6},
            },
            "required": ["service", "environment", "alert_time"],
        },
    ),
    "service_context": (
        service_context,
        "Service owner, on-call role, escalation chain and (optional) business-impact scoring.",
        {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "severity": {"type": "string"},
                "environment": {"type": "string"},
                "duration_minutes": {"type": "integer", "default": 60},
            },
            "required": ["service"],
        },
    ),
    "similar_incidents": (
        similar_incidents,
        "Find historically similar incidents with root cause, resolution and MTTR.",
        {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "symptom": {"type": "string"},
                "environment": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["service", "symptom"],
        },
    ),
    "escalation_preview": (
        escalation_preview,
        "Read-only escalation policy preview (masked recipient). Never sends notifications.",
        {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "severity": {"type": "string"},
            },
            "required": ["service"],
        },
    ),
}


def list_tools() -> list[dict[str, Any]]:
    return [
        {"name": name, "description": desc, "inputSchema": schema}
        for name, (_, desc, schema) in TOOLS.items()
    ]


class UnknownToolError(KeyError):
    """Raised when a tool name is not in the registry (JSON-RPC method-not-found)."""


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOLS:
        raise UnknownToolError(f"unknown tool: {name}")
    handler, _, _ = TOOLS[name]
    return handler(arguments or {})
