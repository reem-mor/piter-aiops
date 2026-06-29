"""Normalize RAG/triage payloads to the final API response contract."""
from __future__ import annotations

from typing import Any

from app.services.structured_analysis import build_structured_analysis, strip_markdown
from app.text_utils import format_answer_sections


def _join_lines(items: Any) -> str:
    if isinstance(items, str):
        return items.strip()
    if not isinstance(items, list):
        return ""
    parts: list[str] = []
    for item in items:
        text = str(item).strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def _escalation_text(raw: Any) -> str:
    if isinstance(raw, list):
        return "; ".join(str(x).strip() for x in raw if str(x).strip())
    return str(raw or "").strip()


def piter_block(
    *,
    answer: str,
    piter_sections: dict[str, Any] | None = None,
    answer_sections: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Build the required ``piter`` object with five string fields."""
    sections = dict(piter_sections or {})
    parsed = answer_sections or format_answer_sections(answer)
    if not sections and parsed.get("piter_sections"):
        sections = dict(parsed["piter_sections"])

    triage_plan = sections.get("triage_plan") or parsed.get("steps") or []
    triage = str(sections.get("triage") or "").strip()
    if not triage and triage_plan:
        triage = "\n".join(
            f"{idx}. {step}" for idx, step in enumerate(triage_plan, start=1)
        )

    investigation = str(sections.get("investigation") or "").strip()
    if not investigation:
        investigation = str(parsed.get("summary") or "").strip()

    priority = str(sections.get("priority") or "").strip()
    if not priority and answer:
        for line in answer.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("priority:"):
                priority = stripped.split(":", 1)[-1].strip()
                break

    return {
        "priority": priority,
        "investigation": investigation,
        "triage": triage,
        "escalation": _escalation_text(sections.get("escalation") or parsed.get("escalation")),
        "resolution": str(sections.get("resolution") or "").strip(),
    }


def _sources_from_citations(citations: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in citations or []:
        if isinstance(item, dict):
            out.append(
                {
                    "document": item.get("document") or item.get("source_label") or "Unknown",
                    "excerpt": item.get("excerpt") or item.get("snippet") or item.get("preview") or "",
                    "score": item.get("score"),
                    "source_uri": item.get("source_uri"),
                }
            )
        else:
            out.append({"document": str(item), "excerpt": ""})
    return out


def _confidence_from_sections(piter_sections: dict[str, Any] | None) -> str:
    raw = str((piter_sections or {}).get("confidence") or "").strip().lower()
    if not raw:
        return "medium"
    if "high" in raw:
        return "high"
    if "low" in raw:
        return "low"
    return "medium"


def _next_action(piter: dict[str, str], recommended_steps: list[str] | None) -> str:
    if recommended_steps:
        for step in recommended_steps:
            candidate = str(step).strip()
            if candidate and not candidate.lower().endswith("runbook"):
                return candidate
    triage = piter.get("triage") or ""
    if triage:
        for line in triage.splitlines():
            first = line.strip()
            candidate = first.lstrip("0123456789.) ").strip()
            if candidate and not candidate.lower().endswith("runbook"):
                return candidate
    return piter.get("escalation") or "Review cited runbooks and validate service health."


def _tool_results_from_enrichment(enrichment: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not enrichment:
        return []
    results: list[dict[str, Any]] = []
    if enrichment.get("deployments") is not None or enrichment.get("likely_deploy_correlation") is not None:
        results.append(
            {
                "name": "get_recent_deployments",
                "result": {
                    "deployments": enrichment.get("deployments", []),
                    "likely_deploy_correlation": enrichment.get("likely_deploy_correlation"),
                },
            }
        )
    if enrichment.get("owner_team"):
        results.append(
            {
                "name": "get_service_context",
                "result": {"owner_team": enrichment.get("owner_team"), **enrichment},
            }
        )
    if enrichment.get("similar_incidents") is not None:
        results.append(
            {
                "name": "find_similar_incidents",
                "result": enrichment.get("similar_incidents"),
            }
        )
    for tool in enrichment.get("tools") or []:
        if isinstance(tool, dict):
            results.append({"name": tool.get("tool", "tool"), "result": tool})
    return results


def normalize_api_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Add required final fields while preserving backward-compatible keys."""
    answer = str(payload.get("answer") or "")
    piter_sections = payload.get("piter_sections") or payload.get("piter")
    if isinstance(piter_sections, dict) and "triage_plan" in piter_sections:
        pass
    elif isinstance(piter_sections, dict) and "priority" in piter_sections and "triage" in piter_sections:
        # Already normalized piter block — rebuild sections for parsing helpers.
        piter_sections = {
            "priority": piter_sections.get("priority"),
            "investigation": piter_sections.get("investigation"),
            "triage_plan": _join_lines(piter_sections.get("triage", "").splitlines()),
            "escalation": piter_sections.get("escalation"),
            "resolution": piter_sections.get("resolution"),
            "business_impact": payload.get("business_impact"),
            "confidence": payload.get("confidence"),
        }

    answer_sections = payload.get("answer_sections")
    piter = piter_block(
        answer=answer,
        piter_sections=piter_sections if isinstance(piter_sections, dict) else None,
        answer_sections=answer_sections if isinstance(answer_sections, dict) else None,
    )

    citations = payload.get("citations") or []
    sources = payload.get("sources")
    if not sources:
        sources = _sources_from_citations(citations)
    elif citations:
        cite_keys = {
            (
                str(c.get("document") or c.get("source_label") or ""),
                str(c.get("excerpt") or c.get("snippet") or "")[:80],
            )
            for c in citations
            if isinstance(c, dict)
        }
        sources = [
            s
            for s in sources
            if isinstance(s, dict)
            and (
                str(s.get("document") or ""),
                str(s.get("excerpt") or "")[:80],
            )
            not in cite_keys
        ]

    tool_results = payload.get("tool_results")
    if tool_results is None:
        tool_results = _tool_results_from_enrichment(payload.get("enrichment"))

    business_impact = payload.get("business_impact")
    if isinstance(business_impact, dict):
        business_impact = business_impact.get("business_explanation") or ""
    if not business_impact:
        if isinstance(piter_sections, dict):
            business_impact = piter_sections.get("business_impact") or ""
        impact = payload.get("impact")
        if isinstance(impact, dict) and impact.get("business_explanation"):
            business_impact = impact["business_explanation"]

    recommended_raw = payload.get("recommended_steps") or []
    recommended = [strip_markdown(str(step)) for step in recommended_raw if str(step).strip()]
    confidence = payload.get("confidence") or _confidence_from_sections(
        piter_sections if isinstance(piter_sections, dict) else None
    )

    impact = payload.get("impact")
    if isinstance(impact, dict):
        impact = dict(impact)
        if business_impact and not impact.get("business_explanation"):
            impact["business_explanation"] = business_impact
        if business_impact and not impact.get("business_impact"):
            impact["business_impact"] = business_impact

    normalized = dict(payload)
    if isinstance(impact, dict):
        normalized["impact"] = impact

    det_sections = payload.get("deterministic_piter_sections")
    structured_piter = piter
    if isinstance(det_sections, dict) and det_sections.get("investigation"):
        structured_piter = {
            "priority": str(det_sections.get("priority") or piter.get("priority") or ""),
            "investigation": str(det_sections.get("investigation") or ""),
            "triage": str(det_sections.get("triage") or piter.get("triage") or ""),
            "escalation": _escalation_text(det_sections.get("escalation") or piter.get("escalation")),
            "resolution": str(det_sections.get("resolution") or piter.get("resolution") or ""),
        }

    structured = build_structured_analysis(
        {
            **payload,
            "piter": structured_piter,
            "recommended_steps": recommended,
            "business_impact": business_impact or payload.get("business_impact") or "",
        }
    )
    normalized.update(
        {
            "answer": answer,
            "piter": piter,
            "piter_sections": piter_sections if isinstance(piter_sections, dict) else None,
            "business_impact": business_impact or "",
            "next_action": payload.get("next_action") or _next_action(piter, recommended),
            "confidence": confidence,
            "sources": sources,
            "tool_results": tool_results or [],
            "fallback_used": bool(payload.get("fallback_used")),
            "recommended_steps": recommended,
            "structured_analysis": structured,
        }
    )
    memory = payload.get("memory")
    if isinstance(memory, dict):
        normalized["memory"] = memory
    return normalized
