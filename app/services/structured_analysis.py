"""Build a single structured analysis view for API responses and UI rendering."""
from __future__ import annotations

import re
from typing import Any

_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_MD_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MD_BULLET = re.compile(r"^[-*•]\s+", re.MULTILINE)
_MD_NUMBERED = re.compile(r"^\d+\.\s+", re.MULTILINE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z*])")

_EVIDENCE_MAX_ITEMS = 5
_EVIDENCE_MAX_CHARS = 160
_SUMMARY_MAX_SENTENCES = 2
_ACTION_MAX_ITEMS = 8


def strip_markdown(text: str | None) -> str:
    """Remove common markdown markers for plain UI text."""
    if not text:
        return ""
    cleaned = str(text).strip()
    cleaned = _MD_HEADING.sub("", cleaned)
    cleaned = _MD_BOLD.sub(r"\1", cleaned)
    cleaned = _MD_ITALIC.sub(r"\1", cleaned)
    cleaned = _MD_BULLET.sub("", cleaned)
    cleaned = _MD_NUMBERED.sub("", cleaned)
    return cleaned.strip()


def _cap_text(text: str, max_chars: int = _EVIDENCE_MAX_CHARS) -> str:
    cleaned = strip_markdown(text)
    if len(cleaned) <= max_chars:
        return cleaned
    truncated = cleaned[: max_chars - 1].rstrip()
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return f"{truncated}…"


def _normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", strip_markdown(text).lower())


def _is_near_duplicate(candidate: str, existing: list[str]) -> bool:
    key = _normalize_key(candidate)
    if not key:
        return True
    for item in existing:
        other = _normalize_key(item)
        if not other:
            continue
        if key == other or key in other or other in key:
            return True
    return False


def _first_sentences(text: str, max_sentences: int = _SUMMARY_MAX_SENTENCES) -> str:
    cleaned = strip_markdown(text)
    if not cleaned:
        return ""
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(cleaned) if p.strip()]
    if not parts:
        return _cap_text(cleaned, 320)
    return " ".join(parts[:max_sentences])


def _split_text_items(text: str | None, *, max_items: int = 4) -> list[str]:
    if not text:
        return []
    items: list[str] = []
    for raw in re.split(r"\n+", str(text)):
        line = strip_markdown(raw)
        if line:
            items.append(_cap_text(line))
    if len(items) <= 1 and text and len(text) > 180:
        for part in _SENTENCE_SPLIT.split(str(text)):
            chunk = strip_markdown(part)
            if chunk and len(chunk) > 12:
                items.append(_cap_text(chunk))
    return items[:max_items]


def _normalize_steps(steps: Any) -> list[str]:
    if not steps:
        return []
    if isinstance(steps, str):
        return _split_text_items(steps, max_items=_ACTION_MAX_ITEMS)
    if not isinstance(steps, list):
        return []
    out: list[str] = []
    for step in steps:
        if isinstance(step, str):
            if "\n" in step:
                out.extend(_split_text_items(step, max_items=_ACTION_MAX_ITEMS))
            else:
                capped = _cap_text(step, 200)
                if capped:
                    out.append(capped)
        elif step:
            capped = _cap_text(str(step), 200)
            if capped:
                out.append(capped)
    deduped: list[str] = []
    for item in out:
        if not _is_near_duplicate(item, deduped):
            deduped.append(item)
    return deduped[:_ACTION_MAX_ITEMS]


def _similar_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("similar_incidents") or []
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in raw[:8]:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "incident_id": str(item.get("incident_id") or item.get("id") or ""),
                "service": str(item.get("service") or ""),
                "summary": _cap_text(
                    str(item.get("summary") or item.get("symptom") or item.get("title") or item.get("root_cause") or ""),
                    140,
                ),
                "mttr_minutes": item.get("mttr_minutes"),
            }
        )
    return [r for r in rows if r.get("incident_id") or r.get("summary")]


def _correlation_chain(payload: dict[str, Any]) -> list[dict[str, str]]:
    chain: list[dict[str, str]] = []
    dep = payload.get("suspect_deployment")
    alert = payload.get("alert") if isinstance(payload.get("alert"), dict) else {}
    similar = _similar_rows(payload)

    if isinstance(dep, dict) and dep:
        version = str(dep.get("version") or "").strip()
        service = str(dep.get("service") or alert.get("service") or "").strip()
        ts = str(dep.get("deployed_at") or dep.get("timestamp") or "").strip()
        detail = _cap_text(str(dep.get("change_summary") or dep.get("summary") or ""), 120)
        label = f"{service} {version}".strip() if version else service
        chain.append(
            {
                "step": "deployment",
                "label": label or "Recent deployment",
                "timestamp": ts,
                "detail": detail or "Suspect deployment correlated to alert window",
            }
        )

    if alert:
        service = str(alert.get("service") or "").strip()
        env = str(alert.get("environment") or "").strip()
        symptom = _cap_text(
            str(alert.get("symptom") or alert.get("title") or alert.get("description") or ""),
            120,
        )
        chain.append(
            {
                "step": "alert",
                "label": f"{service} · {env}".strip(" ·") or "Active alert",
                "timestamp": str(alert.get("alert_time") or alert.get("timestamp") or ""),
                "detail": symptom or "Alert triggered investigation",
            }
        )

    if similar:
        first = similar[0]
        chain.append(
            {
                "step": "similar_incident",
                "label": str(first.get("incident_id") or "Similar incident"),
                "timestamp": "",
                "detail": str(first.get("summary") or "Historical match from past incidents"),
            }
        )

    return chain


def _evidence(payload: dict[str, Any], *, summary: str) -> list[str]:
    """Prefer deterministic facts; avoid prose walls and summary duplication."""
    evidence: list[str] = []
    alert = payload.get("alert") if isinstance(payload.get("alert"), dict) else {}
    if alert:
        svc = str(alert.get("service") or "").strip()
        env = str(alert.get("environment") or "").strip()
        if svc or env:
            evidence.append(f"Alert evidence: {svc} · {env}".strip(" ·"))

    runbook = str(payload.get("matched_runbook") or "").strip()
    if runbook:
        evidence.append(f"Matched runbook: {runbook}")

    dep = payload.get("suspect_deployment")
    if isinstance(dep, dict) and dep.get("version"):
        evidence.append(
            _cap_text(
                f"Deployment {dep.get('service')} {dep.get('version')} at "
                f"{dep.get('deployed_at') or dep.get('timestamp') or 'recent window'}",
                140,
            )
        )

    similar = _similar_rows(payload)
    if similar:
        first = similar[0]
        evidence.append(
            _cap_text(
                f"Similar incident {first.get('incident_id')}: {first.get('summary')}",
                140,
            )
        )

    deployment_reason = str(payload.get("deployment_reason") or "").strip()
    if deployment_reason:
        evidence.append(_cap_text(deployment_reason, 140))

    priority_rationale = str(payload.get("priority_rationale") or "").strip()
    if priority_rationale:
        evidence.append(_cap_text(priority_rationale, 140))

    deduped: list[str] = []
    for item in evidence:
        if _is_near_duplicate(item, deduped) or _is_near_duplicate(item, [summary]):
            continue
        deduped.append(item)
        if len(deduped) >= _EVIDENCE_MAX_ITEMS:
            break
    return deduped


def _tools_called(payload: dict[str, Any]) -> list[str]:
    tool_results = payload.get("tool_results") or []
    if not isinstance(tool_results, list):
        return []
    names: list[str] = []
    for item in tool_results:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("tool") or "").strip()
            if name and name not in names:
                names.append(name)
    return names


def _detected_pattern(payload: dict[str, Any], similar: list[dict[str, Any]]) -> str:
    explicit = str(payload.get("detected_pattern") or "").strip()
    if explicit:
        return _cap_text(explicit, 120)
    alert = payload.get("alert") if isinstance(payload.get("alert"), dict) else {}
    service = str(alert.get("service") or "").strip()
    if similar:
        count = len(similar)
        return f"{count} similar incident{'s' if count != 1 else ''} matched for {service or 'service'}"
    symptom = str(alert.get("symptom") or alert.get("title") or "").strip()
    if symptom:
        return _cap_text(symptom, 120)
    return "Single-service alert pattern under investigation"


def _log_enrichment(payload: dict[str, Any], tools: list[str]) -> str:
    explicit = str(payload.get("log_enrichment") or "").strip()
    if explicit:
        return _cap_text(explicit, 120)
    if "get_recent_deployments" in tools and "find_similar_incidents" in tools:
        return "Deploy correlation + incident history enriched via MCP tools"
    if tools:
        return f"Enriched via {len(tools)} MCP tool{'s' if len(tools) != 1 else ''}"
    return "Structured dataset enrichment (logs pending MCP query)"


def _escalation_suggestion(payload: dict[str, Any]) -> dict[str, Any]:
    owner = payload.get("owner") if isinstance(payload.get("owner"), dict) else {}
    policy = payload.get("escalation_policy") if isinstance(payload.get("escalation_policy"), dict) else {}
    piter = payload.get("piter") if isinstance(payload.get("piter"), dict) else {}
    notify = policy.get("notify")
    path = owner.get("escalation_path") or owner.get("escalation_chain")
    if isinstance(path, list):
        path_text = " → ".join(str(x) for x in path if x)
    else:
        path_text = str(path or "")
    if isinstance(notify, list) and notify:
        path_text = " → ".join(str(x) for x in notify if x)
    summary = strip_markdown(str(piter.get("escalation") or policy.get("summary") or path_text))
    return {
        "owner_team": str(owner.get("owner_team") or ""),
        "primary_oncall": str(owner.get("primary_oncall") or owner.get("primary_on_call") or ""),
        "escalation_path": strip_markdown(path_text),
        "requires_escalation": bool(payload.get("requires_escalation")),
        "summary": _cap_text(summary, 200),
    }


def build_structured_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize triage/chat payloads into the structured analysis contract."""
    piter = payload.get("piter") if isinstance(payload.get("piter"), dict) else {}
    severity = str(payload.get("priority") or piter.get("priority") or "P3").strip()

    impact = payload.get("impact")
    business_impact = payload.get("business_impact")
    if isinstance(business_impact, dict):
        business_impact = business_impact.get("business_explanation") or ""
    if isinstance(impact, dict) and not business_impact:
        business_impact = impact.get("business_explanation") or impact.get("business_impact") or ""

    summary_source = str(business_impact or "").strip()
    if not summary_source:
        summary_source = str(piter.get("investigation") or "").strip()
    summary = _first_sentences(summary_source) if summary_source else ""

    recommended = _normalize_steps(payload.get("recommended_steps"))
    if not recommended:
        recommended = _normalize_steps(piter.get("triage"))

    similar = _similar_rows(payload)
    tools_called = _tools_called(payload)
    noise = payload.get("noise_suppressed")
    noise_val = int(noise) if noise is not None and str(noise).isdigit() else None

    return {
        "severity": severity,
        "summary": summary,
        "correlation_chain": _correlation_chain(payload),
        "evidence": _evidence(payload, summary=summary),
        "similar_incidents": similar,
        "recommended_actions": recommended,
        "escalation_suggestion": _escalation_suggestion(payload),
        "detected_pattern": _detected_pattern(payload, similar),
        "log_enrichment": _log_enrichment(payload, tools_called),
        "tools_called": tools_called,
        "noise_suppressed": noise_val,
    }
