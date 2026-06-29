"""Incident triage orchestration: RAG + 4 tools + session memory.

Backend-agnostic: callers pass an ``ask_fn(question) -> RagAnswer`` so the same
orchestration drives both the local offline client and the Bedrock client (with
fallback handled by the caller). The output matches the PITER AiOps triage card
JSON contract.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from flask import has_app_context

from app.bedrock_client import RagAnswer
from app.services import session_memory
from app.services.alert_stream import p1_demo_alert
from app.services.incident_analysis import analyze_incident, compose_piter_answer, compose_piter_sections
from app.services.local_rag import _first_excerpt_steps
from app.services.tool_router import decide_tools, run_plan
from app.text_utils import parse_action_bullets

AskFn = Callable[..., RagAnswer]

def get_demo_alert() -> dict[str, Any]:
    """P1 storm trigger from data/source/alert_stream.csv (single source of truth)."""
    return p1_demo_alert()


# Backward-compatible alias; always resolves from CSV at call time.
def _demo_alert_dict() -> dict[str, Any]:
    return get_demo_alert()


class _DemoAlertProxy:
    """Dict-like proxy so legacy ``DEMO_ALERT['service']`` reads stay CSV-backed."""

    def __getitem__(self, key: str) -> Any:
        return _demo_alert_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return _demo_alert_dict().get(key, default)

    def __iter__(self):
        return iter(_demo_alert_dict())

    def keys(self):
        return _demo_alert_dict().keys()

    def items(self):
        return _demo_alert_dict().items()

    def values(self):
        return _demo_alert_dict().values()

    def __repr__(self) -> str:
        return repr(_demo_alert_dict())


DEMO_ALERT: Any = _DemoAlertProxy()


def build_triage_question(alert: dict[str, Any]) -> str:
    """Build the retrieval query sent to the RAG backend."""
    symptom = str(alert.get("symptom") or alert.get("description") or "").strip()
    service = str(alert.get("service", "")).strip()
    pieces = [symptom or "incident"]
    if service:
        pieces.append(service)
    return " ".join(pieces).strip()


def _citations_payload(rag: RagAnswer) -> list[dict[str, Any]]:
    return [
        {
            "document": c.source_label,
            "excerpt": c.snippet,
            "score": c.score,
        }
        for c in rag.citations
    ]


def _recommended_steps(
    rag: RagAnswer,
    *,
    piter_sections: dict[str, Any] | None = None,
) -> list[str]:
    """Best-effort recommended steps from PITER sections, answer, or citations."""
    if piter_sections and piter_sections.get("triage_plan"):
        return list(piter_sections["triage_plan"])[:8]
    steps = parse_action_bullets(rag.answer)
    if len(steps) >= 2:
        return steps[:8]
    best: list[str] = steps
    for citation in rag.citations:
        candidate = _first_excerpt_steps(citation.snippet)
        if len(candidate) > len(best):
            best = candidate
    return best[:8]


def _tool_outputs_from_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Map structured analysis fields to the legacy tool output envelope."""
    return {
        "structured_analysis": analysis,
        "correlate_deployments": analysis.get("deployments", {}),
        "lookup_owner_and_escalation": analysis.get("owner", {}),
        "score_business_impact": analysis.get("impact", {}),
        "find_similar_incidents": analysis.get("similar_incidents", {}),
    }


def _deterministic_next_action(analysis: dict[str, Any]) -> str:
    """Return an alert-aligned next action from structured data."""
    alert = analysis.get("alert", {}) if isinstance(analysis, dict) else {}
    service = str(alert.get("service", "")).strip()
    symptom = str(alert.get("symptom") or alert.get("description") or "").lower()
    deploys = analysis.get("deployments", {}) if isinstance(analysis, dict) else {}
    likely_deploy = isinstance(deploys, dict) and bool(deploys.get("likely_deploy_correlation"))
    if service == "auth-service":
        if likely_deploy or "deploy" in symptom:
            return (
                "Confirm auth-service scope, check the latest deployment, then validate "
                "Redis token store and customer-db health before rollback."
            )
        return "Confirm auth-service error rate, Redis token health, and customer-db connectivity."
    if likely_deploy:
        return "Validate the suspect deployment and prepare rollback if metrics degraded after release."
    return "Confirm scope, dependency health, owner, and business impact before mitigation."


def _active_owner(card: dict[str, Any], tools: dict[str, Any]) -> dict[str, Any]:
    owner = card.get("owner")
    if isinstance(owner, dict) and owner:
        return owner
    legacy = tools.get("lookup_owner_and_escalation", {})
    return legacy if isinstance(legacy, dict) else {}


def _active_correlate(card: dict[str, Any], tools: dict[str, Any]) -> dict[str, Any]:
    if card.get("suspect_deploys") is not None or card.get("deployment_reason"):
        return {
            "deployments": card.get("suspect_deploys", []),
            "suspect_deployment": card.get("suspect_deployment"),
            "reason": card.get("deployment_reason", ""),
        }
    legacy = tools.get("correlate_deployments", {})
    return legacy if isinstance(legacy, dict) else {}


def _active_impact(card: dict[str, Any], tools: dict[str, Any]) -> dict[str, Any]:
    impact = card.get("impact")
    if isinstance(impact, dict) and impact:
        return impact
    legacy = tools.get("score_business_impact", {})
    return legacy if isinstance(legacy, dict) else {}


def run_triage(
    alert: dict[str, Any],
    *,
    ask_fn: AskFn,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Run full triage: structured analysis, RAG, compose one triage card."""
    sid = session_memory.create_session(alert, session_id=session_id)
    question = build_triage_question(alert)

    app_ctx = None
    if has_app_context():
        from flask import current_app

        app_ctx = current_app._get_current_object()

    def _invoke_rag() -> RagAnswer:
        def _call() -> RagAnswer:
            try:
                return ask_fn(question, session_id=sid)
            except TypeError:
                return ask_fn(question)

        if app_ctx is not None:
            with app_ctx.app_context():
                return _call()
        return _call()

    with ThreadPoolExecutor(max_workers=2) as pool:
        rag_future = pool.submit(_invoke_rag)
        analysis_future = pool.submit(analyze_incident, alert)
        rag = rag_future.result()
        analysis = analysis_future.result()
    analysis_ok = not analysis.get("error")

    if analysis_ok:
        correlate = analysis.get("deployments", {})
        owner = analysis.get("owner", {})
        impact = analysis.get("impact", {})
        similar = analysis.get("similar_incidents", {})
        tool_outputs = _tool_outputs_from_analysis(analysis)
    else:
        tool_outputs = run_plan(decide_tools(alert))
        correlate = tool_outputs.get("correlate_deployments", {})
        owner = tool_outputs.get("lookup_owner_and_escalation", {})
        impact = tool_outputs.get("score_business_impact", {})
        similar = tool_outputs.get("find_similar_incidents", {})

    answer_sections = compose_piter_sections(analysis if analysis_ok else {}, rag.answer)
    piter_sections = answer_sections.get("piter_sections")
    composed_answer = compose_piter_answer(
        analysis if analysis_ok else {},
        rag_answer=rag.answer,
    )
    deterministic_sections = compose_piter_sections(analysis if analysis_ok else {}, rag_answer="")
    deterministic_piter_sections = deterministic_sections.get("piter_sections")

    citations = _citations_payload(rag)
    if analysis_ok:
        kb = analysis.get("knowledge_base", {})
        if kb.get("found"):
            citations.append({
                "document": kb.get("runbook_file", "runbook"),
                "excerpt": kb.get("investigation", "")[:400],
                "score": 1.0,
            })

    suspect_deploys = correlate.get("deployments", []) if isinstance(correlate, dict) else []
    deployment_reason = correlate.get("reason", "") if isinstance(correlate, dict) else ""

    priority_info = analysis.get("priority", {}) if analysis_ok else {}
    priority = priority_info.get("priority") or str(alert.get("severity", "P3")).upper()
    requires_escalation = priority_info.get(
        "requires_escalation", priority in {"P1", "P2", "P3"}
    )

    matched_runbook = rag.matched_runbook
    if analysis_ok:
        kb = analysis.get("knowledge_base", {})
        if kb.get("runbook_file"):
            matched_runbook = kb["runbook_file"]

    card: dict[str, Any] = {
        "answer": composed_answer,
        "answer_sections": answer_sections,
        "piter_sections": piter_sections,
        "citations": citations,
        "recommended_steps": _recommended_steps(rag, piter_sections=piter_sections),
        "suspect_deploys": suspect_deploys,
        "suspect_deployment": correlate.get("suspect_deployment") if isinstance(correlate, dict) else None,
        "deployment_reason": deployment_reason,
        "owner": owner,
        "impact": impact,
        "similar_incidents": similar.get("similar_incidents", []) if isinstance(similar, dict) else similar,
        "grounded": rag.grounded or bool(analysis_ok),
        "matched_runbook": matched_runbook,
        "session_id": sid,
        "memory_used": False,
        "mode": rag.mode,
        "alert": analysis.get("alert", alert) if analysis_ok else alert,
        "priority": priority,
        "priority_rationale": priority_info.get("rationale", ""),
        "escalation_policy": analysis.get("escalation", {}) if analysis_ok else {},
        "sources": analysis.get("sources", []) if analysis_ok else [],
        "requires_escalation": requires_escalation,
        "next_action": _deterministic_next_action(analysis) if analysis_ok else "",
        "piter_stages": {
            "priority": "complete",
            "investigation": "complete",
            "triage": "complete",
            "escalation": "complete" if requires_escalation else "skipped",
            "resolution": "pending",
        },
        "deterministic_piter_sections": deterministic_piter_sections,
        "business_impact": (
            impact.get("business_explanation") if isinstance(impact, dict) else ""
        )
        or "",
    }

    session_memory.save_triage(
        sid,
        citations=citations,
        tool_outputs=tool_outputs,
        triage_card=card,
    )
    return card


def _classify_followup(question: str) -> str:
    q = question.lower()
    if any(k in q for k in ("escalate", "who do i", "owner", "on-call", "on call", "contact")):
        return "owner"
    if any(k in q for k in ("deploy", "deployment", "rollback", "cause", "what caused")):
        return "deploy"
    if any(k in q for k in ("sql", "command", "query", "show me")):
        return "sql"
    if any(k in q for k in ("impact", "cost", "revenue", "business", "sla", "regulatory")):
        return "impact"
    if any(k in q for k in ("summarize", "summary", "recap", "tl;dr")):
        return "summary"
    return "general"


def run_follow_up(
    session_id: str,
    question: str,
    *,
    ask_fn: AskFn,
) -> dict[str, Any] | None:
    """Answer a follow-up using stored triage card context; re-run RAG only if needed."""
    session = session_memory.get_session(session_id)
    if session is None:
        return None

    tools = session.get("tool_outputs", {}) or {}
    card = session.get("triage_card", {}) or {}
    kind = _classify_followup(question)
    memory_used = True
    mode = card.get("mode", "local")

    if kind == "owner":
        owner = _active_owner(card, tools)
        escalation = card.get("escalation_policy") or {}
        chain = " -> ".join(owner.get("escalation_chain", [])) or owner.get("escalation_path", "")
        notify = escalation.get("notify")
        if isinstance(notify, list) and notify:
            chain = " -> ".join(notify)
        primary = owner.get("primary_on_call") or owner.get("primary_on_call_role", "the on-call")
        answer = (
            f"Escalate to {primary} "
            f"(team {owner.get('owner_team', 'n/a')}, Slack {owner.get('slack_channel', 'n/a')}). "
            f"Escalation chain: {chain}. "
            f"Secondary: {owner.get('secondary_on_call') or owner.get('secondary_on_call_role', 'n/a')}."
        )
        payload = {"answer": answer, "owner": owner}
    elif kind == "deploy":
        correlate = _active_correlate(card, tools)
        suspect = correlate.get("suspect_deployment")
        answer = correlate.get("reason") or card.get("deployment_reason") or "No suspect deployment found in the window."
        payload = {
            "answer": answer,
            "suspect_deployment": suspect,
            "suspect_deploys": correlate.get("deployments", card.get("suspect_deploys", [])),
        }
    elif kind == "impact":
        impact = _active_impact(card, tools)
        answer = impact.get("business_explanation", "No business impact estimate available.")
        payload = {"answer": answer, "impact": impact}
    elif kind == "summary":
        owner = _active_owner(card, tools)
        impact = _active_impact(card, tools)
        answer = (
            f"Runbook: {card.get('matched_runbook', 'n/a')}. "
            f"Owner: {owner.get('owner_team', 'n/a')} ({owner.get('primary_on_call') or owner.get('primary_on_call_role', 'n/a')}). "
            f"Impact: {impact.get('sla_risk', 'n/a')} SLA risk, "
            f"~${impact.get('estimated_total_cost', 0):,} so far. "
            f"{len(card.get('recommended_steps', []))} recommended steps."
        )
        payload = {"answer": answer, "summary_of": card.get("matched_runbook")}
    else:
        memory_used = False
        # Inline the active incident context: Bedrock agents do not reliably
        # surface sessionAttributes in the prompt, so a bare "What should I
        # check first?" would otherwise be answered without incident data.
        alert = session.get("alert") or card.get("alert") or {}
        scoped_question = question
        if isinstance(alert, dict) and alert.get("service"):
            header = " ".join(
                str(alert.get(k) or "").strip()
                for k in ("severity", "service", "environment")
                if alert.get(k)
            )
            symptom = str(alert.get("symptom") or alert.get("description") or "").strip()
            scoped_question = (
                f"Active incident: {header}"
                + (f" — {symptom}" if symptom else "")
                + f". Operator follow-up question: {question}"
            )
        try:
            rag = ask_fn(scoped_question, session_id=session_id)
        except TypeError:
            rag = ask_fn(scoped_question)
        mode = rag.mode
        payload = {
            "answer": rag.answer,
            "citations": _citations_payload(rag),
            "grounded": rag.grounded,
        }

    result = {
        **payload,
        "session_id": session_id,
        "memory_used": memory_used,
        "mode": mode,
        "kind": kind,
    }
    session_memory.append_followup(session_id, question, result)
    return result
