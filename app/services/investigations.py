"""Build investigation cards from live alert-stream data (no hardcoded UI rows)."""
from __future__ import annotations

from typing import Any

from app.services.alert_stream import load_active_alerts, summarize_alert_stream
from app.enrichment_tools import score_business_impact


_CONCLUSION_BY_SEVERITY: dict[str, str] = {
    "P1": "Critical",
    "P2": "Suspicious",
    "P3": "Inconclusive",
    "P4": "Noise",
}


_STATUS_BY_SEVERITY: dict[str, str] = {
    "P1": "Escalated",
    "P2": "Investigating",
    "P3": "Monitoring",
    "P4": "Noise Grouped",
}


def _impact_label(service: str, environment: str, severity: str) -> str:
    impact = score_business_impact(
        service=service,
        environment=environment,
        severity=severity,
        duration_minutes=60,
    )
    if impact.get("error"):
        return "Impact not quantified"
    revenue = impact.get("revenue_impact_usd_per_hour")
    regulatory = impact.get("regulatory_risk")
    if revenue:
        suffix = " regulated market exposure" if regulatory == "high" else " revenue at risk"
        return f"${int(revenue):,}/hr{suffix}"
    return str(impact.get("business_explanation") or "Impact not quantified")


def alert_row_to_investigation(row: dict[str, str], *, index: int) -> dict[str, Any]:
    """Map one alert-stream CSV row to the SPA Investigation shape."""
    service = str(row.get("service") or "unknown")
    environment = str(row.get("environment") or "")
    severity = str(row.get("severity") or "P4").upper()
    alert_id = str(row.get("alert_id") or f"INV-{index:03d}")
    description = str(row.get("title") or row.get("description") or row.get("symptom") or "Alert")
    alert_time = str(row.get("alert_time") or row.get("timestamp") or "")
    entities = str(row.get("entities") or row.get("affected_components") or service)
    is_noise = str(row.get("is_noise_candidate", "")).lower() == "true"
    conclusion = "Noise" if is_noise else _CONCLUSION_BY_SEVERITY.get(severity, "Inconclusive")
    status = "Noise Grouped" if is_noise else _STATUS_BY_SEVERITY.get(severity, "Monitoring")
    detail = (
        f"{severity} {service} — {description[:120]}"
        if not is_noise
        else f"Noise grouped: {description[:120]}"
    )
    return {
        "id": alert_id,
        "conclusion": conclusion,
        "conclusionDetail": detail,
        "alertTime": alert_time[-8:] if len(alert_time) >= 8 else alert_time,
        "alert": f"{severity} {service} {description[:80]}",
        "service": service,
        "environment": environment,
        "entities": entities,
        "source": "Alert stream + enrichment APIs",
        "status": status,
        "priority": severity if severity in {"P1", "P2", "P3", "P4"} else "P4",
        "impact": _impact_label(service, environment, severity),
    }


def build_investigations(*, limit: int = 12) -> dict[str, Any]:
    """Return investigation cards derived from the deterministic alert storm."""
    summary = summarize_alert_stream()
    rows = load_active_alerts(limit=limit)
    investigations = [
        alert_row_to_investigation(row, index=i + 1) for i, row in enumerate(rows)
    ]
    return {
        "investigations": investigations,
        "summary": {
            "total": summary.get("total", 0),
            "active_count": summary.get("active_count", len(investigations)),
            "noise_suppressed": summary.get("noise_suppressed", 0),
            "p1_trigger": summary.get("p1_trigger"),
        },
    }
