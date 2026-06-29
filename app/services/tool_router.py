"""MCP-style tool registry and JSON tool-calling router.

Mirrors the teacher's pattern: the model (or, in deterministic demo mode, the
orchestrator) emits a JSON decision ``{"tool": name, "arguments": {...}}`` and
the router validates and executes it against the real Python tool functions in
:mod:`app.enrichment_tools`. The same registry can describe the tools to a
Bedrock Agent or be exposed later as MCP/Lambda handlers.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

from app.enrichment_tools import (
    correlate_deployments,
    find_similar_incidents,
    lookup_owner_and_escalation,
    score_business_impact,
)

log = logging.getLogger(__name__)

# Tool registry: name -> {description, parameters (JSON-schema-ish), handler}.
TOOLS: dict[str, dict[str, Any]] = {
    "correlate_deployments": {
        "description": "Find recent deployments related to the affected service and its dependency hops near the alert time.",
        "parameters": {
            "service": "string (required)",
            "environment": "string (required)",
            "alert_time": "ISO-8601 string (required)",
            "window_minutes": "integer (optional)",
        },
        "handler": correlate_deployments,
    },
    "lookup_owner_and_escalation": {
        "description": "Find owner team, on-call, secondary escalation, Slack channel, escalation chain, and dependencies for a service.",
        "parameters": {
            "service": "string (required)",
            "severity": "string (optional)",
        },
        "handler": lookup_owner_and_escalation,
    },
    "score_business_impact": {
        "description": "Estimate revenue cost, SLA risk, and regulatory risk for an incident.",
        "parameters": {
            "service": "string (required)",
            "environment": "string (required)",
            "severity": "string (required)",
            "duration_minutes": "integer (optional)",
        },
        "handler": score_business_impact,
    },
    "find_similar_incidents": {
        "description": "Find similar past incidents, their root cause, resolution, and MTTR.",
        "parameters": {
            "service": "string (required)",
            "symptom": "string (required)",
            "environment": "string (optional)",
            "top_k": "integer (optional)",
        },
        "handler": find_similar_incidents,
    },
}


def tool_specs() -> list[dict[str, Any]]:
    """Return the public tool specs (name, description, parameters) for prompts."""
    return [
        {"name": name, "description": meta["description"], "parameters": meta["parameters"]}
        for name, meta in TOOLS.items()
    ]


def decide_tools(alert: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the deterministic JSON tool plan for a triage alert.

    For triage we run all four tools (the teacher's deterministic flow). Each
    decision is a ``{"tool", "arguments"}`` object — the same JSON contract a
    model would emit.
    """
    service = str(alert.get("service", "")).strip()
    environment = str(alert.get("environment", "")).strip()
    severity = str(alert.get("severity", "")).strip()
    symptom = str(alert.get("symptom") or alert.get("description") or "").strip()
    alert_time = str(alert.get("alert_time", "")).strip()
    duration = alert.get("duration_minutes", 60)

    return [
        {
            "tool": "correlate_deployments",
            "arguments": {
                "service": service,
                "environment": environment,
                "alert_time": alert_time,
            },
        },
        {
            "tool": "lookup_owner_and_escalation",
            "arguments": {
                "service": service,
                "severity": severity,
                "environment": environment,
            },
        },
        {
            "tool": "score_business_impact",
            "arguments": {
                "service": service,
                "environment": environment,
                "severity": severity,
                "duration_minutes": duration,
                "alert": alert,
            },
        },
        {
            "tool": "find_similar_incidents",
            "arguments": {
                "service": service,
                "symptom": symptom,
                "environment": environment,
                "top_k": 3,
            },
        },
    ]


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute one tool by name with keyword arguments; never raises.

    Returns the tool's structured dict, or ``{"error": ...}`` for an unknown
    tool or an unexpected failure, so the orchestrator stays resilient.
    """
    spec = TOOLS.get(name)
    if spec is None:
        return {"error": f"Unknown tool '{name}'"}
    handler: Callable[..., dict[str, Any]] = spec["handler"]
    try:
        return handler(**(arguments or {}))
    except Exception as exc:  # noqa: BLE001 — tools must never crash the app
        log.exception("Tool %s failed", name)
        return {"error": f"Tool '{name}' failed: {exc}"}


def run_plan(plan: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Execute a list of ``{"tool","arguments"}`` decisions; return by tool name."""
    results: dict[str, dict[str, Any]] = {}
    for decision in plan:
        if isinstance(decision, str):
            decision = json.loads(decision)
        name = decision.get("tool", "")
        results[name] = execute_tool(name, decision.get("arguments", {}))
    return results
