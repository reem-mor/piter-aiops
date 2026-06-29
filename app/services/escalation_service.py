"""Invoke piter-escalation Lambda handler locally for Flask API routes."""
from __future__ import annotations

import importlib.util
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LAMBDA_PATH = ROOT / "action_groups" / "piter-escalation" / "lambda_function.py"


@lru_cache(maxsize=1)
def _load_escalation_lambda():
    spec = importlib.util.spec_from_file_location("piter_escalation_lambda", LAMBDA_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load escalation lambda from {LAMBDA_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mask_recipient(recipient: str) -> str:
    if not recipient:
        return ""
    if len(recipient) <= 4:
        return "*" * len(recipient)
    return f"{recipient[:2]}***{recipient[-2:]}"


def _first_env(*names: str) -> str:
    """Return the first non-empty environment value among names."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def resolve_demo_recipients(channel: str) -> list[str]:
    """Resolve all escalation recipients for a channel from environment variables ONLY.

    Values may be comma/semicolon-separated to support multi-recipient escalation
    (e.g. PITER_ESCALATION_EMAIL="a@x.com,b@y.com"). Recipients are never read
    from git or request bodies.
    """
    channel = channel.strip().lower()
    if channel == "sms":
        raw = _first_env("PITER_ESCALATION_SMS", "PITER_DEMO_SMS_RECIPIENT")
    elif channel == "whatsapp":
        raw = _first_env(
            "PITER_ESCALATION_SMS",
            "PITER_DEMO_WHATSAPP_RECIPIENT",
            "PITER_DEMO_SMS_RECIPIENT",
        )
    elif channel == "email":
        raw = _first_env("PITER_ESCALATION_EMAIL", "PITER_DEMO_EMAIL_RECIPIENT")
    else:
        raise ValueError(f"Unknown channel: {channel}")
    seen: set[str] = set()
    recipients: list[str] = []
    for part in raw.replace(";", ",").split(","):
        value = part.strip()
        if value and value.lower() not in seen:
            seen.add(value.lower())
            recipients.append(value)
    return recipients


def resolve_demo_recipient(channel: str) -> str:
    """Resolve the primary escalation recipient (first configured) for a channel."""
    recipients = resolve_demo_recipients(channel)
    return recipients[0] if recipients else ""


def _build_event(operation: str, params: dict[str, str]) -> dict[str, Any]:
    items = [{"name": key, "type": "string", "value": value} for key, value in params.items()]
    if "operation" not in params:
        items.append({"name": "operation", "type": "string", "value": operation})
    return {
        "messageVersion": "1.0",
        "actionGroup": "piter-escalation",
        "apiPath": "/escalation",
        "httpMethod": "POST",
        "parameters": items,
        "sessionAttributes": {},
        "promptSessionAttributes": {},
    }


def invoke_escalation(operation: str, params: dict[str, str]) -> dict[str, Any]:
    mod = _load_escalation_lambda()
    response = mod.lambda_handler(_build_event(operation, params), None)
    raw = response["response"]["responseBody"]["application/json"]["body"]
    body = json.loads(raw)
    return {
        "http_status": int(response["response"]["httpStatusCode"]),
        **body,
    }


def notify_demo_channel(
    *,
    channel: str,
    incident_id: str,
    service: str,
    severity: str,
    confirmation_token: str,
    message: str | None = None,
    subject: str | None = None,
    html_body: str | None = None,
    escalation_context: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    from app.services.escalation_message import enrich_escalation_context, format_escalation_messages

    recipients = resolve_demo_recipients(channel)
    if not recipients:
        return {
            "http_status": 400,
            "ok": False,
            "error": (
                f"No escalation recipient configured for {channel}: set "
                f"PITER_ESCALATION_{'EMAIL' if channel == 'email' else 'SMS'} on the instance"
            ),
            "sent": False,
        }
    ctx = enrich_escalation_context(
        escalation_context,
        incident_id=incident_id,
        service=service,
        severity=severity,
    )
    formatted = format_escalation_messages(
        ctx,
        channel="sms" if channel == "whatsapp" else channel,
    )
    default_message = formatted["body"]
    html = html_body or formatted.get("html_body") or ""

    deliveries: list[dict[str, Any]] = []
    last_result: dict[str, Any] = {}
    any_sent = False
    for recipient in recipients:
        params: dict[str, str] = {
            "operation": "live_notify",
            "service": service,
            "severity": severity,
            "incident_id": incident_id,
            "recipient": recipient,
            "message": message or default_message,
            "subject": subject or formatted.get("subject") or "",
            "confirmation_token": confirmation_token,
            "delivery_channel": channel,
        }
        if html and channel == "email":
            params["html_body"] = html
        if idempotency_key:
            params["idempotency_key"] = f"{idempotency_key}:{recipient}"
        else:
            params["idempotency_key"] = f"{incident_id}:{channel}:{recipient}:{severity}"
        result = invoke_escalation("live_notify", params)
        last_result = result
        sent = bool(result.get("sent"))
        any_sent = any_sent or sent
        deliveries.append(
            {
                "recipient": mask_recipient(recipient),
                "sent": sent,
                "ok": bool(result.get("ok", sent)),
                "error": result.get("error") or result.get("reason"),
                "message_id": result.get("message_id"),
            }
        )

    aggregate = dict(last_result)
    aggregate["recipient_configured"] = True
    aggregate["channel"] = channel
    aggregate["sent"] = any_sent
    aggregate["ok"] = any_sent or bool(last_result.get("ok"))
    aggregate["recipients_total"] = len(recipients)
    aggregate["recipients_sent"] = sum(1 for item in deliveries if item["sent"])
    aggregate["deliveries"] = deliveries
    if any_sent:
        aggregate["http_status"] = 200
        if aggregate["recipients_sent"] < len(recipients):
            aggregate["partial_failure"] = True
            failed = [item for item in deliveries if not item["sent"]]
            aggregate["partial_failure_detail"] = "; ".join(
                f"{item['recipient']}: {item['error']}" for item in failed if item.get("error")
            )
        aggregate.pop("error", None)
    return aggregate
