"""Recent deployment lookup tool for PITER AiOps."""
from __future__ import annotations

from typing import Any

from app.enrichment_tools import correlate_deployments


def get_recent_deployments(
    service: str,
    environment: str = "production",
    alert_time: str = "2026-06-08T09:00:00Z",
) -> dict[str, Any]:
    """Return recent deployments for a service and environment."""
    if not service or not service.strip():
        return {"error": "Missing service", "deployments": []}
    return correlate_deployments(
        service=service.strip(),
        environment=environment.strip() or "production",
        alert_time=alert_time,
    )
