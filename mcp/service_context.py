"""Service context lookup tool for PITER AiOps."""
from __future__ import annotations

from typing import Any

from app.enrichment_tools import lookup_owner_and_escalation


def get_service_context(service: str) -> dict[str, Any]:
    """Return owner, dependency, and escalation context for a service."""
    if not service or not service.strip():
        return {"error": "Missing service"}
    return lookup_owner_and_escalation(service=service.strip())
