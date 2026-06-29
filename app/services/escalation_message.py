"""Format on-call escalation notifications from structured incident context."""
from __future__ import annotations

import os
from html import escape
from typing import Any


def _war_room_channel(ctx: dict[str, Any]) -> str:
    return (
        str(ctx.get("war_room_channel") or "").strip()
        or os.environ.get("PITER_ESCALATION_WAR_ROOM_SLACK", "#war-room").strip()
        or "#war-room"
    )


def _lines_actions(actions: list[Any]) -> list[str]:
    out: list[str] = []
    for idx, item in enumerate(actions[:8], start=1):
        text = str(item).strip()
        if text:
            out.append(f"{idx}. {text}")
    return out


def format_escalation_messages(
    ctx: dict[str, Any],
    *,
    channel: str = "email",
) -> dict[str, str]:
    """Return subject, plain-text body, and optional HTML body for escalation."""
    severity = str(ctx.get("severity") or "P1").upper()
    service = str(ctx.get("service") or "unknown-service")
    incident_id = str(ctx.get("incident_id") or "INC-UNKNOWN")
    environment = str(ctx.get("environment") or "").strip()
    title = str(ctx.get("incident_title") or ctx.get("summary") or f"{severity} on {service}").strip()
    on_call = str(ctx.get("on_call_name") or ctx.get("primary_on_call") or "on-call engineer").strip()
    owner_team = str(ctx.get("owner_team") or "Service owner team").strip()
    slack_team = str(ctx.get("slack_channel") or "#incidents").strip()
    war_room = _war_room_channel(ctx)
    business = str(
        ctx.get("business_impact")
        or ctx.get("business_explanation")
        or "Customer-facing degradation; revenue and SLA exposure under assessment.",
    ).strip()
    support = str(
        ctx.get("support_complaints")
        or ctx.get("customer_support")
        or "Support ticket volume elevated vs baseline; monitor CSAT and social channels.",
    ).strip()
    top_error = str(
        ctx.get("top_error")
        or ctx.get("top_logs")
        or "See incident dashboard for dominant error signatures.",
    ).strip()
    deployment = str(
        ctx.get("recent_deployment")
        or ctx.get("deploy_summary")
        or "Check piter-recent-deployments for correlated change.",
    ).strip()
    actions = ctx.get("recommended_actions") or ctx.get("recommended_steps") or []
    if isinstance(actions, str):
        actions = [line.strip() for line in actions.split("\n") if line.strip()]
    action_lines = _lines_actions(list(actions))
    runbook_count = int(ctx.get("runbook_count") or len(ctx.get("runbook_sources") or []) or 0)
    runbook_name = str(ctx.get("runbook_name") or ctx.get("matched_runbook") or "").strip()
    runbook_line = (
        f"{runbook_count} grounded sources"
        if runbook_count
        else (runbook_name or "Runbooks available in PITER console")
    )

    env_suffix = f" ({environment})" if environment else ""
    subject = str(ctx.get("subject") or "").strip() or (
        f"[PITER {severity}] {title} — {service}{env_suffix}"
    )

    greeting = f"Hey {on_call} — you're the {severity} on-call for {service}."
    body_parts = [
        greeting,
        "",
        "We need your help on an active production incident. Please treat this as urgent.",
        "",
        f"INCIDENT: {severity} — {title}",
        f"Incident ID: {incident_id}",
        f"Service: {service}{env_suffix}",
        f"Owner team: {owner_team}",
        "",
        "WHAT'S HAPPENING",
        title,
        "",
        "BUSINESS IMPACT",
        business,
        "",
        "CUSTOMER / SUPPORT SIGNALS",
        support,
        "",
        "TOP ERROR / LOGS",
        top_error,
        "",
        "RECENT DEPLOYMENT",
        deployment,
        "",
        "RECOMMENDED FIRST ACTIONS",
        *(action_lines or ["1. Acknowledge incident and join war room.", "2. Review runbook and recent deploy."]),
        "",
        "RUNBOOK SOURCES",
        runbook_line + (f" ({runbook_name})" if runbook_name and runbook_count else ""),
        "",
        f"Please join {war_room} on Slack immediately — NOC is coordinating bridge access.",
        f"Your team channel: {slack_team}",
        "",
        "— PITER Ops (automated escalation)",
    ]
    text_body = "\n".join(body_parts)

    if channel == "sms":
        # Keep SMS GSM-friendly and short — long/topic-routed bodies often fail sandbox delivery.
        title_short = " ".join(title.split())[:55]
        room = war_room.lstrip("#")
        sms = (
            f"PITER {severity} {service}{env_suffix}: {title_short}. "
            f"On-call {on_call}. Join {room}. Ack {incident_id}"
        )
        return {"subject": subject, "body": sms[:160], "html_body": ""}

    html_body = _render_html(
        severity=severity,
        title=title,
        incident_id=incident_id,
        service=service,
        environment=environment,
        on_call=on_call,
        owner_team=owner_team,
        business=business,
        support=support,
        top_error=top_error,
        deployment=deployment,
        action_lines=action_lines,
        runbook_line=runbook_line,
        runbook_name=runbook_name,
        war_room=war_room,
        slack_team=slack_team,
    )
    return {"subject": subject, "body": text_body, "html_body": html_body}


def enrich_escalation_context(
    ctx: dict[str, Any] | None,
    *,
    incident_id: str,
    service: str,
    severity: str,
) -> dict[str, Any]:
    """Fill missing escalation fields from enrichment tools when possible."""
    merged: dict[str, Any] = dict(ctx or {})
    merged.setdefault("incident_id", incident_id)
    merged.setdefault("service", service)
    merged.setdefault("severity", severity)

    try:
        from app.enrichment_tools import lookup_owner_and_escalation, score_business_impact

        owner = lookup_owner_and_escalation(service=service, severity=severity)
        if "error" not in owner:
            merged.setdefault("on_call_name", owner.get("primary_on_call"))
            merged.setdefault("owner_team", owner.get("owner_team"))
            merged.setdefault("slack_channel", owner.get("slack_channel"))
            merged.setdefault("escalation_path", owner.get("escalation_path"))

        env = str(merged.get("environment") or "GIB-UKGC")
        impact = score_business_impact(
            service=service,
            environment=env,
            severity=severity,
            duration_minutes=int(merged.get("duration_minutes") or 15),
        )
        merged.setdefault("business_impact", impact.get("business_explanation"))
        if impact.get("player_impact_pct"):
            pct = impact["player_impact_pct"]
            merged.setdefault(
                "support_complaints",
                f"Estimated {pct}% player impact; support queues and social mentions likely elevated.",
            )
    except Exception:
        pass

    return merged


def _render_html(
    *,
    severity: str,
    title: str,
    incident_id: str,
    service: str,
    environment: str,
    on_call: str,
    owner_team: str,
    business: str,
    support: str,
    top_error: str,
    deployment: str,
    action_lines: list[str],
    runbook_line: str,
    runbook_name: str,
    war_room: str,
    slack_team: str,
) -> str:
    env_line = f" ({escape(environment)})" if environment else ""
    actions_html = "".join(f"<li>{escape(line)}</li>" for line in action_lines) or (
        "<li>Acknowledge and join war room</li><li>Review runbook and recent deploy</li>"
    )
    runbook_suffix = f" — {escape(runbook_name)}" if runbook_name else ""
    return f"""<!DOCTYPE html>
<html><body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.5;color:#1e293b;max-width:640px">
  <p style="font-size:16px;margin:0 0 12px">Hey <strong>{escape(on_call)}</strong> — you're the
  <strong style="color:#b45309">{escape(severity)}</strong> on-call for <strong>{escape(service)}</strong>.</p>
  <p>We need your help on an active production incident. Please treat this as <strong>urgent</strong>.</p>
  <div style="background:#fef2f2;border-left:4px solid #dc2626;padding:12px 16px;margin:16px 0">
    <div style="font-size:12px;text-transform:uppercase;color:#991b1b;letter-spacing:.05em">Incident</div>
    <div style="font-size:18px;font-weight:600;margin-top:4px">{escape(severity)} — {escape(title)}</div>
    <div style="font-size:13px;margin-top:8px;color:#475569">
      ID: {escape(incident_id)} · Service: {escape(service)}{env_line}<br>
      Team: {escape(owner_team)}
    </div>
  </div>
  <h3 style="font-size:13px;text-transform:uppercase;color:#64748b;margin:20px 0 8px">Business impact</h3>
  <p>{escape(business)}</p>
  <h3 style="font-size:13px;text-transform:uppercase;color:#64748b;margin:20px 0 8px">Customer / support</h3>
  <p>{escape(support)}</p>
  <h3 style="font-size:13px;text-transform:uppercase;color:#64748b;margin:20px 0 8px">Top error / logs</h3>
  <p><code style="background:#f1f5f9;padding:2px 6px;border-radius:4px">{escape(top_error)}</code></p>
  <h3 style="font-size:13px;text-transform:uppercase;color:#64748b;margin:20px 0 8px">Recent deployment</h3>
  <p>{escape(deployment)}</p>
  <h3 style="font-size:13px;text-transform:uppercase;color:#64748b;margin:20px 0 8px">Recommended first actions</h3>
  <ol style="padding-left:20px">{actions_html}</ol>
  <h3 style="font-size:13px;text-transform:uppercase;color:#64748b;margin:20px 0 8px">Runbook sources</h3>
  <p>{escape(runbook_line)}{runbook_suffix}</p>
  <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px;margin:24px 0">
    <strong>Action required:</strong> Join <strong>{escape(war_room)}</strong> on Slack now.
    Team channel: {escape(slack_team)}.
  </div>
  <p style="font-size:12px;color:#94a3b8">— PITER Ops (automated escalation)</p>
</body></html>"""
