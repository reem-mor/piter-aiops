"""Structured incident analysis from canonical data/source datasets + KB runbooks."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.environment_codes import normalize_environment
from app.services import data_access
from app.text_utils import format_answer_sections

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_KB_RUNBOOKS = _PROJECT_ROOT / "knowledge_base" / "runbooks"

_SEVERITY_COST_KEY = {
    "P1": "p1_cost_per_minute_usd",
    "P2": "p2_cost_per_minute_usd",
    "P3": "p3_cost_per_minute_usd",
    "P4": "p4_cost_per_minute_usd",
}
_SEVERITY_ALIASES = {
    "CRITICAL": "P1",
    "HIGH": "P2",
    "MEDIUM": "P3",
    "MODERATE": "P3",
    "LOW": "P4",
}

_ENV_REGULATOR = {
    "GIB-UKGC": "UKGC",
    "NJ-DGE": "DGE",
    "MGM": "MGM",
}


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _normalize_priority_label(value: str) -> str:
    raw = (value or "").strip().upper()
    return _SEVERITY_ALIASES.get(raw, raw if raw in {"P1", "P2", "P3", "P4"} else "P3")


def _normalize_alert(alert: dict[str, Any], source_dir: Path | None) -> dict[str, Any]:
    """Merge caller payload with resolved source row when possible."""
    merged = dict(alert)
    resolved = data_access.resolve_alert(
        alert_id=str(alert.get("alert_id", "")),
        service=str(alert.get("service", "")),
        environment=str(alert.get("environment", "")),
        source_dir=source_dir,
    )
    if resolved:
        for key, value in resolved.items():
            if value and not merged.get(key):
                merged[key] = value
        if resolved.get("title") and not merged.get("symptom"):
            merged["symptom"] = resolved["title"]
            merged["description"] = resolved["title"]
        if resolved.get("timestamp") and not merged.get("alert_time"):
            merged["alert_time"] = resolved["timestamp"]
    return merged


def _find_service_owner(service: str, source_dir: Path | None) -> dict[str, Any] | None:
    svc = service.strip().lower()
    for row in data_access.load_service_owners(source_dir):
        if row["service"].lower() == svc:
            deps = [d.strip() for d in row.get("dependencies", "").split("|") if d.strip()]
            regulatory = [
                r.strip() for r in row.get("regulatory_exposure", "").split("|") if r.strip()
            ]
            return {
                "service": row["service"],
                "owner_team": row["owning_team"],
                "team_lead": row.get("team_lead", ""),
                "service_tier": row["service_tier"],
                "business_function": row["business_function"],
                "slack_channel": row["slack_channel"],
                "pagerduty_service": row.get("pagerduty_service_id", ""),
                "primary_on_call": row["primary_on_call_role"],
                "secondary_on_call": row["secondary_on_call_role"],
                "escalation_channel": row["slack_channel"],
                "runbook": row["runbook"],
                "dashboard": row["dashboard"],
                "dependencies": deps,
                "regulatory_exposure": regulatory,
                "display_name": row["service"],
                "escalation_path": f"{row['primary_on_call_role']} -> {row['secondary_on_call_role']}",
                "escalation_chain": [
                    row["primary_on_call_role"],
                    row["secondary_on_call_role"],
                ],
            }
    return None


def _correlate_deployments(
    *,
    service: str,
    environment: str,
    alert_time: str,
    dependencies: list[str],
    lookback_hours: int = 6,
    source_dir: Path | None,
) -> dict[str, Any]:
    if not service or not environment or not alert_time:
        return {"error": "Missing service, environment, or alert_time", "deployments": []}

    try:
        alert_dt = _parse_iso(alert_time)
    except (ValueError, AttributeError):
        return {"error": f"Invalid alert_time '{alert_time}'", "deployments": []}

    cutoff = alert_dt - timedelta(hours=lookback_hours)
    env = normalize_environment(environment)
    hop_targets = {service.lower()} | {d.lower() for d in dependencies}

    matched: list[dict[str, Any]] = []
    for row in data_access.load_source_deploys(source_dir):
        if normalize_environment(row["environment"]) != env:
            continue
        if row["service"].lower() not in hop_targets:
            continue
        try:
            deployed_at = _parse_iso(row["timestamp"])
        except ValueError:
            continue
        if deployed_at < cutoff or deployed_at > alert_dt + timedelta(minutes=30):
            continue
        hop = "direct" if row["service"].lower() == service.lower() else "dependency"
        entry = {
            **row,
            "deployed_at": row["timestamp"],
            "hop": hop,
            "deployment_correlation": True,
        }
        matched.append(entry)

    matched.sort(key=lambda r: r["timestamp"], reverse=True)
    suspect = matched[0] if matched else None
    if suspect:
        reason = (
            f"{suspect['service']} {suspect['version']} deployed at {suspect['timestamp']} "
            f"({suspect['hop']} hop) — '{suspect['change_summary']}'. "
            f"Risk: {suspect.get('risk_level', 'unknown')}; "
            f"rollback_available={suspect.get('rollback_available', 'false')}."
        )
    else:
        reason = "No deployments to the service or its dependencies inside the window."

    return {
        "service": service,
        "environment": env,
        "alert_time": alert_time,
        "deployments": matched,
        "suspect_deployment": suspect,
        "reason": reason,
        "likely_deploy_correlation": bool(matched),
        "dependency_hop_explanation": (
            f"{service} depends on {dependencies or []}; deploys to any hop can cause this alert."
        ),
    }


def _score_business_impact(
    *,
    service: str,
    severity: str,
    alert: dict[str, Any],
    source_dir: Path | None,
) -> dict[str, Any]:
    impact_data = data_access.load_business_impact(source_dir)
    svc_block = impact_data.get("services", {}).get(service, {})
    sev = _normalize_priority_label(severity)
    cost_key = _SEVERITY_COST_KEY.get(sev, "p3_cost_per_minute_usd")
    cost_per_minute = int(svc_block.get(cost_key, svc_block.get("p1_cost_per_minute_usd", 0)))
    active_users = int(alert.get("affected_users") or svc_block.get("active_users_typical", 0))
    revenue_per_hour = cost_per_minute * 60
    regulatory = svc_block.get("regulatory_exposure", [])
    reputation = svc_block.get("reputation_risk", "unknown")
    sla_target = float(svc_block.get("sla_target_uptime_pct", 99.9))
    error_rate = float(alert.get("error_rate_pct") or 0)
    sla_risk = "critical" if sev == "P1" or error_rate >= 50 else (
        "high" if sev == "P2" else "moderate" if sev == "P3" else "low"
    )

    return {
        "service": service,
        "severity": sev,
        "active_users": active_users,
        "cost_per_minute": cost_per_minute,
        "revenue_impact_usd_per_hour": revenue_per_hour,
        "sla_risk": sla_risk,
        "sla_target_uptime_pct": sla_target,
        "regulatory_exposure": regulatory,
        "regulatory_risk": "high" if regulatory else "low",
        "reputation_risk": reputation,
        "business_explanation": (
            f"{sev} on {service}: ~{active_users:,} users affected, "
            f"${cost_per_minute:,}/min (${revenue_per_hour:,}/hr). "
            f"SLA risk {sla_risk}; regulatory exposure {', '.join(regulatory) or 'none'}."
        ),
    }


def _classify_priority(
    *,
    alert: dict[str, Any],
    impact: dict[str, Any],
    source_dir: Path | None,
) -> dict[str, Any]:
    matrix = data_access.load_priority_matrix(source_dir)
    thresholds = matrix.get("thresholds", {})
    raw_sev = _normalize_priority_label(str(alert.get("severity", "")))
    error_rate = float(alert.get("error_rate_pct") or 0)
    cost_per_min = int(impact.get("cost_per_minute", 0))
    regulatory = impact.get("regulatory_exposure", [])

    _rank = {"P4": 0, "P3": 1, "P2": 2, "P1": 3}

    def _raise_priority(current: str, candidate: str) -> str:
        return candidate if _rank.get(candidate, 0) > _rank.get(current, 0) else current

    priority = raw_sev if raw_sev in {"P1", "P2", "P3", "P4"} else "P3"
    rationale_parts: list[str] = []

    if error_rate >= 50 or alert.get("metric_name") == "service_down":
        priority = "P1"
        rationale_parts.append(f"{error_rate}% error rate indicates customer-facing outage")
    elif error_rate >= 5:
        priority = _raise_priority(priority, "P2")

    if cost_per_min >= 5000:
        rationale_parts.append(f"revenue risk ${cost_per_min:,}/min exceeds P1 threshold")
        priority = "P1"
    elif cost_per_min >= 1500:
        priority = _raise_priority(priority, "P2")
        rationale_parts.append("elevated revenue exposure")

    if regulatory and priority in {"P1", "P2"}:
        rationale_parts.append(f"regulated markets: {', '.join(regulatory)}")

    if not rationale_parts:
        for example in matrix.get("examples", []):
            if alert.get("service") in example.get("alert", "") or (
                error_rate >= 50 and example.get("priority") == "P1"
            ):
                rationale_parts.append(example.get("rationale", ""))
                break
        if not rationale_parts:
            rationale_parts.append(thresholds.get(priority, {}).get("description", ""))

    threshold = thresholds.get(priority, {})
    return {
        "priority": priority,
        "rationale": "; ".join(rationale_parts) or threshold.get("description", ""),
        "response_target_minutes": threshold.get("response_minutes", 30),
        "requires_escalation": threshold.get("requires_escalation", priority != "P4"),
    }


def _resolve_escalation(
    *,
    priority: str,
    owner: dict[str, Any],
    environment: str,
    source_dir: Path | None,
) -> dict[str, Any]:
    policies = data_access.load_escalation_policies(source_dir)
    default = policies.get("default_policy", {}).get(priority, {})
    notify_roles = list(default.get("notify_immediately", []))
    role_map = {
        "primary_on_call_role": owner.get("primary_on_call", ""),
        "secondary_on_call_role": owner.get("secondary_on_call", ""),
        "team_lead": owner.get("team_lead", owner.get("owner_team", "")),
        "incident_commander": "Incident Commander",
    }
    notify = [role_map.get(r, r) for r in notify_roles if role_map.get(r, r)]

    regulatory_override: dict[str, Any] = {}
    env = normalize_environment(environment)
    regulator = _ENV_REGULATOR.get(env)
    if regulator:
        override = policies.get("regulatory_overrides", {}).get(regulator, {}).get(priority)
        if override:
            regulatory_override = {
                "regulator": regulator,
                **override,
            }
            for extra in override.get("additional_notify", []):
                notify.append(extra.replace("_", " ").title())

    return {
        "priority": priority,
        "notify": notify,
        "max_response_minutes": default.get("max_response_minutes"),
        "war_room_required": default.get("war_room", False),
        "confirmation_required": default.get(
            "confirmation_required_for_external_notification", False
        ),
        "regulatory_override": regulatory_override,
        "escalation_timing_minutes": default.get("max_response_minutes"),
    }


def _find_similar_incidents(
    *,
    service: str,
    environment: str,
    symptom: str,
    limit: int = 3,
    source_dir: Path | None,
) -> dict[str, Any]:
    svc = service.lower()
    env = normalize_environment(environment)
    tokens = [t for t in symptom.lower().split() if len(t) > 3]
    scored: list[tuple[int, dict[str, str]]] = []

    for row in data_access.load_past_incidents(source_dir):
        if row["service"].lower() != svc:
            continue
        if env and normalize_environment(row.get("environment", "")) != env:
            continue
        text = f"{row.get('title', '')} {row.get('symptoms', '')} {row['root_cause']}".lower()
        score = sum(1 for t in tokens if t in text)
        if "outage" in symptom.lower() or "100%" in symptom:
            if "100%" in text or "outage" in text:
                score += 3
        if "pool" in symptom.lower() and "pool" in text:
            score += 2
        if score > 0 or row.get("severity") == "P1":
            scored.append((score, row))

    scored.sort(key=lambda x: (-x[0], x[1].get("start_time", "")), reverse=False)
    top = scored[:limit]
    similar = [
        {
            "incident_id": r["incident_id"],
            "title": r.get("title", ""),
            "severity": r["severity"],
            "environment": r.get("environment", ""),
            "root_cause": r["root_cause"],
            "resolution": r["resolution"],
            "mttr_minutes": int(r["mttr_minutes"]),
            "lessons_learned": r.get("lessons_learned", ""),
            "related_runbook": r.get("related_runbook", ""),
            "similarity_reason": "same service and environment with matching symptom pattern",
        }
        for _score, r in top
    ]
    return {"similar_incidents": similar, "count": len(similar)}


def _extract_runbook_sections(runbook_file: str) -> dict[str, Any]:
    path = _KB_RUNBOOKS / runbook_file
    if not path.is_file() and runbook_file.endswith(".md"):
        path = _KB_RUNBOOKS / runbook_file.replace(".md", ".json")
    if not path.is_file():
        return {"runbook_file": runbook_file, "found": False}

    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        text = str(payload.get("body", ""))
        runbook_file = path.name
    else:
        text = path.read_text(encoding="utf-8")
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
            continue
        if current and line.strip():
            sections[current].append(line.strip())

    def _join(key: str) -> str:
        return " ".join(sections.get(key, []))

    triage_lines = sections.get("remediation", []) or sections.get("investigation steps", [])
    triage_steps = [
        re.sub(r"^\d+\.\s+", "", ln) for ln in triage_lines if re.match(r"^\d+\.", ln)
    ]

    return {
        "runbook_file": runbook_file,
        "found": True,
        "path": str(path),
        "investigation": _join("investigation steps"),
        "triage_decision_tree": "\n".join(sections.get("triage decision tree", [])),
        "triage_steps": triage_steps[:8],
        "verification": _join("verification"),
        "rollback": _join("rollback"),
        "escalation": _join("escalation"),
        "related": sections.get("related", []),
    }


def analyze_incident(
    alert: dict[str, Any],
    *,
    source_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run the full structured analysis pipeline for an alert."""
    src = Path(source_dir) if source_dir else None
    normalized = _normalize_alert(alert, src)
    service = str(normalized.get("service", "")).strip()
    environment = str(normalized.get("environment", "")).strip()
    alert_time = str(
        normalized.get("alert_time") or normalized.get("timestamp") or ""
    ).strip()
    symptom = str(
        normalized.get("symptom") or normalized.get("description") or normalized.get("title") or ""
    ).strip()

    owner = _find_service_owner(service, src)
    if not owner:
        return {"error": f"Unknown service '{service}'", "alert": normalized}

    deploys = _correlate_deployments(
        service=service,
        environment=environment,
        alert_time=alert_time,
        dependencies=owner.get("dependencies", []),
        source_dir=src,
    )
    severity_hint = str(normalized.get("severity", "P3"))
    impact = _score_business_impact(
        service=service, severity=severity_hint, alert=normalized, source_dir=src
    )
    priority_info = _classify_priority(alert=normalized, impact=impact, source_dir=src)
    priority = priority_info["priority"]
    impact["severity"] = priority

    escalation = _resolve_escalation(
        priority=priority,
        owner=owner,
        environment=environment,
        source_dir=src,
    )
    similar = _find_similar_incidents(
        service=service,
        environment=environment,
        symptom=symptom,
        source_dir=src,
    )
    kb = _extract_runbook_sections(owner.get("runbook", ""))

    sources = [
        f"service_owners.csv ({service})",
        f"deploys.csv ({environment})",
        "business_impact.json",
        "priority_matrix.json",
        "escalation_policies.json",
        "past_incidents.csv",
    ]
    if kb.get("found"):
        sources.append(kb["runbook_file"])

    return {
        "alert": normalized,
        "owner": owner,
        "deployments": deploys,
        "impact": impact,
        "priority": priority_info,
        "escalation": escalation,
        "similar_incidents": similar,
        "knowledge_base": kb,
        "sources": sources,
    }


def compose_piter_answer(analysis: dict[str, Any], rag_answer: str = "") -> str:
    """Build PITER-formatted answer text from structured analysis."""
    if analysis.get("error"):
        return rag_answer or analysis["error"]

    owner = analysis.get("owner", {})
    deploys = analysis.get("deployments", {})
    impact = analysis.get("impact", {})
    priority = analysis.get("priority", {})
    escalation = analysis.get("escalation", {})
    similar = analysis.get("similar_incidents", {})
    kb = analysis.get("knowledge_base", {})
    alert = analysis.get("alert", {})

    suspect = deploys.get("suspect_deployment") or {}
    deploy_line = (
        f"Suspect deploy: {suspect.get('service')} {suspect.get('version')} at "
        f"{suspect.get('timestamp')} ({suspect.get('change_summary', '')})."
        if suspect
        else deploys.get("reason", "No correlated deployment.")
    )

    similar_lines = []
    for inc in similar.get("similar_incidents", [])[:3]:
        similar_lines.append(
            f"{inc['incident_id']}: {inc['root_cause']} — resolved in {inc['mttr_minutes']} min "
            f"({inc.get('lessons_learned', '')})"
        )

    triage_steps = kb.get("triage_steps") or [
        "Confirm scope and error rate in affected environment.",
        "Correlate recent deployments for service and dependencies.",
        "Execute runbook remediation and verify recovery.",
    ]

    lines = [
        "Priority:",
        f"{priority.get('priority')} — {priority.get('rationale')}. "
        f"Response target: {priority.get('response_target_minutes')} minutes.",
        "",
        "Investigation findings:",
        f"Alert on {alert.get('service')} in {alert.get('environment')}: "
        f"{alert.get('symptom') or alert.get('title', '')}. {deploy_line} "
        f"Owner: {owner.get('owner_team')} ({owner.get('service_tier')}). "
        f"Dependencies: {', '.join(owner.get('dependencies', []))}.",
        "",
        "Triage plan:",
        *[f"{i + 1}. {step}" for i, step in enumerate(triage_steps)],
        "",
        "Escalation recommendation:",
        f"Notify: {', '.join(escalation.get('notify', []))}. "
        f"War room: {'required' if escalation.get('war_room_required') else 'not required'}. "
        f"Max response: {escalation.get('max_response_minutes')} min.",
    ]
    reg = escalation.get("regulatory_override") or {}
    if reg:
        lines.append(
            f"Regulatory override ({reg.get('regulator')}): report to {reg.get('report_to')} "
            f"within {reg.get('reporting_window_hours')}h."
        )

    lines.extend([
        "",
        "Resolution plan:",
        kb.get("rollback") or "Follow the deployment rollback runbook if deploy-correlated; otherwise use the service runbook remediation.",
        "",
        "Business impact:",
        impact.get("business_explanation", ""),
        "",
        "Sources:",
        "; ".join(analysis.get("sources", [])),
        "",
        "Confidence and uncertainty:",
        "High confidence on owner, deploy correlation, and priority from structured datasets. "
        "Medium uncertainty on root cause until dependency health checks complete.",
    ])
    if similar_lines:
        lines.insert(
            lines.index("Triage plan:") + 2,
            "Historical: " + " | ".join(similar_lines),
        )

    composed = "\n".join(lines)
    if rag_answer and "Priority:" not in rag_answer:
        return composed
    return rag_answer if rag_answer and "Priority:" in rag_answer else composed


def compose_piter_sections(analysis: dict[str, Any], rag_answer: str = "") -> dict[str, Any]:
    """Return parsed answer_sections including piter_sections dict."""
    text = compose_piter_answer(analysis, rag_answer=rag_answer)
    return format_answer_sections(text)
