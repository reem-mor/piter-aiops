"""Similar incident lookup tool for PITER AiOps."""
from __future__ import annotations

from typing import Any

from app.enrichment_tools import find_similar_incidents


def find_similar_incidents_tool(
    service: str,
    symptom: str,
    severity: str = "",
    environment: str = "",
) -> dict[str, Any]:
    """Return similar historical incidents for service and symptom."""
    if not service or not service.strip():
        return {"error": "Missing service", "similar_incidents": [], "count": 0}
    if not symptom or not symptom.strip():
        return {"error": "Missing symptom", "similar_incidents": [], "count": 0}
    result = find_similar_incidents(
        service=service.strip(),
        symptom=symptom.strip(),
        environment=environment.strip(),
        top_k=3,
    )
    if severity:
        result["severity"] = severity.strip().upper()
    return result
