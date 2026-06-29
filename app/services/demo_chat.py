"""Deterministic demo Q&A and safety guardrails for live presentation.

Answers are grounded in ``data/source/`` and alert storm CSV so they work
identically in local TF-IDF and Bedrock modes without hallucination.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date
from typing import Any

from app.services import data_access
from app.services.alert_stream import load_alert_stream, p1_demo_alert, summarize_alert_stream

_DEMO_DATE = date(2026, 6, 10)

_DESTRUCTIVE = re.compile(
    r"\b("
    r"failover|fail\s*over|traffic\s*shift|delete\s+(the\s+)?(payments?|production|business|customer|wallet|bet)"
    r"|drop\s+table|truncate\s+table|wipe\s+database|destroy\s+(the\s+)?(cluster|database|data\s+source)"
    r"|purge\s+all|remove\s+production\s+data"
    r")\b",
    re.I,
)

_LAST_P1 = re.compile(
    r"(what(?:'s| is)\s+the\s+last\s+p1|last\s+p1\s+alert|most\s+recent\s+p1)",
    re.I,
)
_NOISIEST = re.compile(
    r"(noisiest|most\s+noise|highest\s+noise|which\s+service.*alerting\s+most)",
    re.I,
)
_LAST_DEPLOY = re.compile(
    r"(last\s+deployment|recent\s+deployment|what\s+changed\s+recently|latest\s+deploy)",
    re.I,
)
_DATA_ENGINEER = re.compile(
    r"(data\s+engineer\s+on\s*[- ]?call|who\s+is\s+the\s+data\s+engineer|data\s+platform\s+on\s*[- ]?call)",
    re.I,
)
_LATEST_INCIDENTS = re.compile(
    r"(latest\s+3\s+incidents|last\s+3\s+incidents|recent\s+incidents|what\s+are\s+the\s+latest\s+incidents)",
    re.I,
)


def destructive_action_reply(question: str) -> dict[str, Any] | None:
    """Return a guardrail refusal payload when the operator asks for unsafe actions."""
    q = question.strip()
    if not q or not _DESTRUCTIVE.search(q):
        return None
    action = "that operation"
    if re.search(r"failover|traffic\s*shift", q, re.I):
        action = "autonomous failover or traffic shift"
    elif re.search(r"delete|drop|truncate|wipe|destroy|purge|remove", q, re.I):
        action = "deletion or destruction of production data sources"
    answer = (
        f"**Safety guardrail — action blocked**\n\n"
        f"I cannot execute {action}. PITER Ops is a **recommendation-only** copilot: "
        f"rollback, failover, restarts, and data mutations require **human approval** "
        f"through your change-management process.\n\n"
        f"**What I can do instead:**\n"
        f"1. Show the escalation path and on-call owner\n"
        f"2. Correlate the suspect deployment and runbook steps\n"
        f"3. Draft a post-mortem or incident summary for review\n\n"
        f"_No production systems were modified._"
    )
    return {
        "answer": answer,
        "mode": "guardrail",
        "grounded": True,
        "guardrail_blocked": True,
        "citations": [{"document": "piter/safety_policy.json", "excerpt": "Human approval required for destructive actions.", "score": 1.0}],
        "recommended_followups": [
            "Who should I escalate this to?",
            "What was the last deployment?",
            "Summarize this incident",
        ],
    }


def _current_on_call_for_team(team_substring: str) -> dict[str, str] | None:
    try:
        rows = data_access.load_on_call_schedule()
    except data_access.DataAccessError:
        return None
    team_key = team_substring.lower()
    for row in rows:
        if team_key not in str(row.get("team", "")).lower():
            continue
        start = str(row.get("date_start", ""))[:10]
        end = str(row.get("date_end", ""))[:10]
        if start and end:
            try:
                ds = date.fromisoformat(start)
                de = date.fromisoformat(end)
                if not (ds <= _DEMO_DATE <= de):
                    continue
            except ValueError:
                pass
        return row
    return None


def _noisiest_services(limit: int = 5) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for row in load_alert_stream():
        if str(row.get("is_noise_candidate", "")).lower() == "true":
            svc = str(row.get("service", "")).strip()
            if svc:
                counts[svc] += 1
    return counts.most_common(limit)


def _latest_deployments(limit: int = 3) -> list[dict[str, str]]:
    try:
        deploys = data_access.load_source_deploys()
    except data_access.DataAccessError:
        return []
    sorted_rows = sorted(
        deploys,
        key=lambda r: str(r.get("timestamp", "")),
        reverse=True,
    )
    return sorted_rows[:limit]


def _latest_incidents(limit: int = 3) -> list[dict[str, str]]:
    try:
        incidents = data_access.load_past_incidents()
    except data_access.DataAccessError:
        return []
    sorted_rows = sorted(
        incidents,
        key=lambda r: str(r.get("start_time", r.get("incident_id", ""))),
        reverse=True,
    )
    return sorted_rows[:limit]


def demo_ops_reply(question: str) -> dict[str, Any] | None:
    """Return a grounded demo answer for scripted live-demo questions."""
    q = question.strip()
    if not q:
        return None

    if _LAST_P1.search(q):
        p1 = p1_demo_alert()
        summary = summarize_alert_stream()
        trigger = summary.get("p1_trigger") or {}
        answer = (
            f"**Last P1 alert:** `{trigger.get('alert_id', p1.get('alert_id'))}` — "
            f"**{trigger.get('service', p1.get('service'))}** @ "
            f"{trigger.get('environment', p1.get('environment'))} "
            f"({trigger.get('timestamp', p1.get('alert_time', ''))[:19]}Z)\n\n"
            f"**Summary:** {trigger.get('title', p1.get('symptom'))}\n\n"
            f"Storm corpus: {summary.get('p1_count', 1)} P1 trigger(s) in "
            f"{summary.get('total', 400)} alerts; "
            f"{summary.get('noise_suppressed', 0)} noise candidates suppressed."
        )
        return _demo_payload(
            answer,
            citations=[{"document": "data/source/alert_stream.csv", "excerpt": str(trigger.get("title", "")[:200]), "score": 1.0}],
            tools=["get_alert_stream_summary"],
        )

    if _NOISIEST.search(q):
        ranked = _noisiest_services(5)
        if not ranked:
            return _demo_payload("No noise-pattern data in the alert stream.", tools=[])
        top_svc, top_n = ranked[0]
        lines = [f"**Noisiest service:** `{top_svc}` — **{top_n}** suppressed noise alerts"]
        for svc, n in ranked[1:4]:
            lines.append(f"- `{svc}`: {n} noise alerts")
        answer = "\n".join(lines)
        return _demo_payload(
            answer,
            citations=[{"document": "data/source/alert_stream.csv", "excerpt": f"{top_svc} noise count {top_n}", "score": 1.0}],
            tools=["aggregate_noise_by_service"],
        )

    if _LAST_DEPLOY.search(q):
        deploys = _latest_deployments(3)
        if not deploys:
            return _demo_payload("No deployment records in canonical data/source/deploys.csv.", tools=[])
        latest = deploys[0]
        answer = (
            f"**Most recent deployment:** `{latest.get('deploy_id')}` — "
            f"**{latest.get('service')}** `{latest.get('version')}` → "
            f"{latest.get('environment')} at {str(latest.get('timestamp', ''))[:19]}Z "
            f"({latest.get('status')})\n\n"
            f"**Change:** {latest.get('change_summary', '—')}\n"
            f"**Risk:** {latest.get('risk_level', '—')} · Rollback available: {latest.get('rollback_available', '—')}"
        )
        if len(deploys) > 1:
            answer += "\n\n**Prior deploys:**\n"
            for d in deploys[1:]:
                answer += (
                    f"- {d.get('service')} {d.get('version')} ({d.get('environment')}) "
                    f"— {str(d.get('timestamp', ''))[:10]}\n"
                )
        return _demo_payload(
            answer,
            citations=[{"document": "data/source/deploys.csv", "excerpt": str(latest.get("change_summary", ""))[:200], "score": 1.0}],
            tools=["get_recent_deployments"],
        )

    if _DATA_ENGINEER.search(q):
        row = _current_on_call_for_team("Data Platform")
        if not row:
            return _demo_payload(
                "Data Platform on-call schedule not found in data/source/on_call_schedule.csv.",
                tools=[],
            )
        answer = (
            f"**Data Platform on-call today** ({_DEMO_DATE.isoformat()}):\n\n"
            f"- **Primary:** {row.get('primary_on_call_role', '—')}\n"
            f"- **Secondary:** {row.get('secondary_on_call_role', '—')}\n"
            f"- **Manager escalation:** {row.get('manager_escalation', '—')}\n"
            f"- **Service scope:** {row.get('service', 'replication')} ({row.get('team', 'Data Platform')})\n"
            f"- **PagerDuty:** {row.get('pagerduty_service_id', '—')}"
        )
        return _demo_payload(
            answer,
            citations=[{"document": "data/source/on_call_schedule.csv", "excerpt": row.get("primary_on_call_role", ""), "score": 1.0}],
            tools=["lookup_owner_and_escalation"],
        )

    if _LATEST_INCIDENTS.search(q):
        incidents = _latest_incidents(3)
        if not incidents:
            return _demo_payload("No past incidents in data/source/past_incidents.csv.", tools=[])
        lines = ["**Latest 3 incidents** (from incident history):"]
        for inc in incidents:
            lines.append(
                f"- **{inc.get('incident_id')}** — {inc.get('service')} "
                f"({inc.get('severity')}) · {str(inc.get('start_time', ''))[:10]} — "
                f"{inc.get('title', inc.get('symptoms', ''))[:80]}"
            )
        return _demo_payload(
            "\n".join(lines),
            citations=[{"document": "data/source/past_incidents.csv", "excerpt": incidents[0].get("title", ""), "score": 1.0}],
            tools=["find_similar_incidents"],
        )

    return None


def _demo_payload(
    answer: str,
    *,
    citations: list[dict[str, Any]],
    tools: list[str],
) -> dict[str, Any]:
    tool_results = [{"name": name, "result": {"status": "ok"}} for name in tools]
    return {
        "answer": answer,
        "mode": "demo_grounded",
        "grounded": True,
        "demo_grounded": True,
        "guardrail_blocked": False,
        "citations": citations,
        "tool_results": tool_results,
        "recommended_followups": [
            "What should I check first?",
            "Who should I escalate this to?",
            "Summarize this incident",
        ],
    }
