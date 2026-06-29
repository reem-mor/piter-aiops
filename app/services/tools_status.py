"""Report readiness of the four required enrichment tools."""
from __future__ import annotations

import time
from typing import Any

from app.services.triage_service import get_demo_alert
from app.services.tool_router import TOOLS, execute_tool

# Public labels expected by reviewers and the React demo.
TOOL_STATUS_SPEC: list[dict[str, str]] = [
    {
        "id": "recent_deployments",
        "name": "Recent deployment lookup",
        "tool": "correlate_deployments",
    },
    {
        "id": "service_context",
        "name": "Service context lookup",
        "tool": "lookup_owner_and_escalation",
    },
    {
        "id": "similar_incidents",
        "name": "Similar incidents lookup",
        "tool": "find_similar_incidents",
    },
    {
        "id": "escalation_recommendation",
        "name": "Escalation recommendation",
        "tool": "lookup_owner_and_escalation",
    },
]


def _demo_arguments(tool_name: str) -> dict[str, Any]:
    alert = get_demo_alert()
    service = str(alert.get("service", "")).strip()
    environment = str(alert.get("environment", "")).strip()
    severity = str(alert.get("severity", "")).strip()
    symptom = str(alert.get("symptom") or alert.get("description") or "").strip()
    alert_time = str(alert.get("alert_time", "")).strip()
    duration = alert.get("duration_minutes", 60)

    if tool_name == "correlate_deployments":
        return {
            "service": service,
            "environment": environment,
            "alert_time": alert_time,
        }
    if tool_name == "lookup_owner_and_escalation":
        return {
            "service": service,
            "severity": severity,
            "environment": environment,
        }
    if tool_name == "score_business_impact":
        return {
            "service": service,
            "environment": environment,
            "severity": severity,
            "duration_minutes": duration,
            "alert": alert,
        }
    if tool_name == "find_similar_incidents":
        return {
            "service": service,
            "symptom": symptom,
            "environment": environment,
            "top_k": 3,
        }
    return {}


_TOOLS_STATUS_CACHE: tuple[float, dict[str, Any]] | None = None
_TOOLS_STATUS_TTL_SEC = 30.0


def build_tools_status() -> dict[str, Any]:
    """Probe each required tool with the demo alert and return structured status."""
    global _TOOLS_STATUS_CACHE
    now = time.monotonic()
    if _TOOLS_STATUS_CACHE and now - _TOOLS_STATUS_CACHE[0] < _TOOLS_STATUS_TTL_SEC:
        return _TOOLS_STATUS_CACHE[1]
    payload = _probe_tools_status()
    _TOOLS_STATUS_CACHE = (now, payload)
    return payload


def _probe_tools_status() -> dict[str, Any]:
    tools: list[dict[str, Any]] = []
    all_ready = True

    seen: set[str] = set()
    for spec in TOOL_STATUS_SPEC:
        tool_name = spec["tool"]
        registered = tool_name in TOOLS
        result: dict[str, Any] | None = None
        status = "unavailable"
        message = ""

        if registered and tool_name not in seen:
            result = execute_tool(tool_name, _demo_arguments(tool_name))
            if result.get("error"):
                status = "error"
                message = str(result["error"])
                all_ready = False
            else:
                status = "ready"
            seen.add(tool_name)
        elif registered:
            # Escalation reuses owner lookup — report ready without duplicate probe.
            status = "ready"
            result = {"note": "Uses service context / owner lookup data"}
        else:
            all_ready = False
            message = f"Tool '{tool_name}' is not registered"

        entry: dict[str, Any] = {
            "id": spec["id"],
            "name": spec["name"],
            "tool": tool_name,
            "status": status,
            "registered": registered,
        }
        if message:
            entry["message"] = message
        if result is not None and status == "ready":
            entry["sample_keys"] = sorted(result.keys())[:8]
        tools.append(entry)

    return {
        "all_ready": all_ready,
        "tools": tools,
        "demo_alert": get_demo_alert(),
    }
