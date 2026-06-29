"""PITER AiOps enrichment tools — canonical ``data/source/`` only.

The four enrichment tools (``correlate_deployments``,
``lookup_owner_and_escalation``, ``score_business_impact``,
``find_similar_incidents``) read EXCLUSIVELY from the canonical structured
datasets under ``data/source/`` via :mod:`app.services.data_access` and the
analysis primitives in :mod:`app.services.incident_analysis`.

No legacy ``data/agent_data/``, top-level demo CSV/JSON files, or
``data/sample_documents/`` paths are referenced. Unknown services return a
clean ``{"error": ...}`` envelope instead of falling through to retired data.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services import data_access
from app.services.incident_analysis import (
    _correlate_deployments as _source_correlate,
    _find_service_owner,
    _find_similar_incidents as _source_similar,
    _score_business_impact as _source_impact,
)

_DEFAULT_SOURCE = data_access.source_data_dir()


def _resolve_source_dir(data_dir: Path | None) -> Path:
    """Resolve the canonical source directory (override allowed for tests)."""
    return Path(data_dir) if data_dir else _DEFAULT_SOURCE


def correlate_deployments(
    *,
    service: str,
    environment: str,
    alert_time: str,
    lookback_hours: int = 6,
    window_minutes: int | None = None,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Find recent deploys for a service and its dependency hops near an alert."""
    base = _resolve_source_dir(data_dir)
    if not service or not service.strip():
        return {"error": "Missing service", "deployments": [], "likely_deploy_correlation": False}
    if not environment or not environment.strip():
        return {"error": "Missing environment", "deployments": [], "likely_deploy_correlation": False}
    owner = _find_service_owner(service, base)
    if not owner:
        return {
            "error": f"Unknown service '{service}'",
            "service": service,
            "deployments": [],
            "likely_deploy_correlation": False,
        }
    if window_minutes is not None:
        lookback_hours = max(1, round(window_minutes / 60))
    result = _source_correlate(
        service=service,
        environment=environment,
        alert_time=alert_time,
        dependencies=owner.get("dependencies", []),
        lookback_hours=lookback_hours,
        source_dir=base,
    )
    result.setdefault("service", service)
    result["window_minutes"] = window_minutes
    result["lookback_hours"] = lookback_hours
    return result


def lookup_owner(
    *,
    service: str,
    environment: str,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Return owner team, escalation path, and PagerDuty for a service."""
    base = _resolve_source_dir(data_dir)
    owner = _find_service_owner(service, base)
    if not owner:
        return {"error": f"Unknown service '{service}'"}
    return {
        "service": owner["service"],
        "environment": (environment or "").upper(),
        "owner_team": owner["owner_team"],
        "escalation_path": owner["escalation_path"],
        "pagerduty_service": owner["pagerduty_service"],
        "display_name": owner["display_name"],
    }


def lookup_owner_and_escalation(
    *,
    service: str,
    severity: str = "",
    environment: str = "",
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Return owner team, on-call, escalation chain, Slack channel and deps."""
    base = _resolve_source_dir(data_dir)
    if not service or not service.strip():
        return {"error": "Missing service"}
    owner = _find_service_owner(service, base)
    if not owner:
        return {"error": f"Unknown service '{service}'", "service": service}
    return {
        "service": owner["service"],
        "display_name": owner["display_name"],
        "severity": (severity or "").upper(),
        "owner_team": owner["owner_team"],
        "primary_on_call": owner["primary_on_call"],
        "secondary_escalation": owner["secondary_on_call"],
        "slack_channel": owner["slack_channel"],
        "pagerduty_service": owner["pagerduty_service"],
        "escalation_path": owner["escalation_path"],
        "escalation_chain": owner["escalation_chain"],
        "dependencies": {
            "depends_on": owner["dependencies"],
            "depended_by": [],
        },
        "runbook": owner.get("runbook", ""),
        "dashboard": owner.get("dashboard", ""),
        "business_function": owner.get("business_function", ""),
        "service_tier": owner.get("service_tier", ""),
    }


def score_business_impact(
    *,
    service: str,
    environment: str,
    severity: str,
    duration_minutes: int = 60,
    alert: dict[str, Any] | None = None,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Estimate incident cost and risk from canonical ``business_impact.json``."""
    base = _resolve_source_dir(data_dir)
    try:
        duration = max(0, int(duration_minutes))
    except (TypeError, ValueError):
        duration = 60
    sev = severity.upper() if severity else ""

    owner = _find_service_owner(service, base)
    if not owner:
        return {"error": f"Unknown service '{service}'", "service": service}

    impact = _source_impact(
        service=service,
        severity=sev,
        alert=alert or {},
        source_dir=base,
    )
    revenue_per_hour = impact["revenue_impact_usd_per_hour"]
    cost_per_15min = round(revenue_per_hour / 4)
    estimated_total_cost = round(revenue_per_hour * (duration / 60))
    tier_str = owner.get("service_tier", "tier-2")
    tier = int(tier_str.replace("tier-", "")) if "tier-" in tier_str else 2
    return {
        **impact,
        "environment": environment.upper() if environment else "",
        "duration_minutes": duration,
        "tier": tier,
        "cost_per_15min": cost_per_15min,
        "estimated_total_cost": estimated_total_cost,
        "regulatory_flag": impact.get("regulatory_risk") == "high",
        "escalation_minutes": 5 if sev == "P1" else 15 if sev == "P2" else 30,
        "fallback": False,
    }


def find_similar_incidents(
    *,
    service: str,
    symptom: str,
    environment: str = "",
    limit: int = 5,
    top_k: int | None = None,
    history_path: Path | None = None,  # accepted for backward compat; unused
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Find past incidents similar to the current symptom for a service."""
    max_results = top_k if top_k is not None else limit
    max_results = max(1, int(max_results or 1))
    base = _resolve_source_dir(data_dir)
    result = _source_similar(
        service=service,
        environment=environment,
        symptom=symptom,
        limit=max_results,
        source_dir=base,
    )
    return {
        "service": service,
        "symptom": symptom,
        "environment": (environment or "").upper(),
        **result,
    }


def enrich_triage_demo(
    *,
    service: str = "bet-service",
    environment: str = "GIB-UKGC",
    severity: str = "P1",
    symptom: str = "CRITICAL: bet-service nodes unresponsive — 100% error rate on GIB-UKGC",
    alert_time: str = "2026-06-10T10:02:55Z",
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Full enrichment bundle for the canonical P1 demo scenario."""
    base = data_dir or _DEFAULT_SOURCE
    alert = {"affected_users": 32000, "error_rate_pct": 100}
    return {
        "correlate_deployments": correlate_deployments(
            service=service,
            environment=environment,
            alert_time=alert_time,
            data_dir=base,
        ),
        "lookup_owner": lookup_owner(service=service, environment=environment, data_dir=base),
        "score_business_impact": score_business_impact(
            service=service,
            environment=environment,
            severity=severity,
            alert=alert,
            data_dir=base,
        ),
        "find_similar_incidents": find_similar_incidents(
            service=service, symptom=symptom, environment=environment, data_dir=base
        ),
    }
