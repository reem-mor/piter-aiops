"""Simple callable registry for the four PITER MCP-style tools."""
from __future__ import annotations

from typing import Any, Callable

from mcp.escalation import get_escalation_recommendation
from mcp.recent_deployments import get_recent_deployments
from mcp.service_context import get_service_context
from mcp.similar_incidents import find_similar_incidents_tool

ToolHandler = Callable[..., dict[str, Any]]

TOOLS: dict[str, ToolHandler] = {
    "get_recent_deployments": get_recent_deployments,
    "get_service_context": get_service_context,
    "find_similar_incidents": find_similar_incidents_tool,
    "get_escalation_recommendation": get_escalation_recommendation,
}


def list_registered_tools() -> list[str]:
    return sorted(TOOLS)


def call_registered_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    handler = TOOLS.get(name)
    if handler is None:
        return {"error": f"Unknown tool '{name}'"}
    try:
        return handler(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Tool '{name}' failed: {exc}"}
