"""HTTP routes: SPA bootstrap, JSON API, uploads, /health."""
from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_wtf.csrf import generate_csrf

from app.bedrock_agent_client import build_session_attributes
from app.bedrock_client import BedrockRagClient, RagAnswer
from app.rag_factory import RagClient, get_local_client, get_rag_client
from app.config import Config
from app.data_loader import flat_example_questions, grouped_example_questions
from app.errors import BedrockError
from app.spa import _SPA_ROOT, spa_enabled
from app.upload_service import DocumentUploadService
from app.upload_validators import ALLOWED_UPLOAD_SUFFIXES
from app.validators import MAX_QUESTION_LEN, validate_question
from app.services.alert_stream import load_active_alerts, load_alert_stream, summarize_alert_stream
from app.services.kb_manifest import kb_sections, load_kb_manifest
from app.services.escalation_service import notify_demo_channel
from app.services.escalation_service import resolve_demo_recipients
from app.services.notification_dispatch import (
    allowlist_count,
    check_sms_account_ready_cached,
    email_configured,
    live_dispatch_enabled,
    sms_configured,
    whatsapp_configured,
)
from app.services.triage_service import get_demo_alert, run_follow_up, run_triage
from app.services import session_memory
from app.services.chat_intent import small_talk_reply, structured_chat_reply
from app.services.chat_history import append_turn, clear_history, get_messages
from app.services.response_format import normalize_api_response
from app.services.tools_status import build_tools_status
from app.services.metrics_service import (
    business_impact_metrics,
    escalation_preview_metrics,
    recent_deployments_metrics,
    service_context_metrics,
    similar_incidents_metrics,
)
from app.services.investigations import build_investigations
from app.services.incident_status import all_statuses, set_status

log = logging.getLogger(__name__)
bp = Blueprint("main", __name__)

_VALIDATION_CODES = {"empty_question", "short_question", "oversize_question", "stopwords_only"}


def _app_config() -> Config:
    cfg = current_app.config.get("PITER_CONFIG")
    if isinstance(cfg, Config):
        return cfg
    return Config.from_env()


def _client() -> RagClient:
    cached = current_app.extensions.get("bedrock_client")
    if cached is None:
        cached = get_rag_client(_app_config())
        current_app.extensions["bedrock_client"] = cached
    return cached


def _local_client() -> RagClient:
    cached = current_app.extensions.get("local_client")
    if cached is None:
        cached = get_local_client()
        current_app.extensions["local_client"] = cached
    return cached


def _triage_client() -> RagClient:
    """Triage-only RAG: direct KB RetrieveAndGenerate when agent backend is active."""
    cached = current_app.extensions.get("triage_client")
    if cached is not None:
        return cached
    cfg = _app_config()
    if cfg.USE_BEDROCK and cfg.RAG_BACKEND == "agent":
        cached = BedrockRagClient(cfg)
    else:
        cached = _client()
    current_app.extensions["triage_client"] = cached
    return cached


def _ask_fn_for_triage():
    """Fast triage path: single KB round-trip; chat/follow-up stay on Bedrock Agent."""

    def ask(question: str, *, session_id: str | None = None) -> RagAnswer:
        # RetrieveAndGenerate session IDs are Bedrock-issued; local triage memory IDs are not valid.
        _ = session_id
        return _triage_client().ask(question)

    return ask


def _fallback_enabled() -> bool:
    """Local TF-IDF fallback when Bedrock/KB fails — controlled by PITER_LOCAL_FALLBACK."""
    explicit = current_app.config.get("LOCAL_FALLBACK")
    if explicit is not None:
        return bool(explicit)
    return _app_config().LOCAL_FALLBACK


def _upload_service() -> DocumentUploadService:
    cached = current_app.extensions.get("upload_service")
    if cached is None:
        cached = DocumentUploadService(_app_config())
        current_app.extensions["upload_service"] = cached
    return cached


def _wants_json() -> bool:
    if request.headers.get("HX-Request"):
        return False
    if request.args.get("format") == "json":
        return True
    if request.is_json:
        return True
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return best == "application/json" and request.accept_mimetypes[best] >= request.accept_mimetypes["text/html"]


def _cfg_get(key: str, default: str = "") -> str:
    """Read Flask config keys set via Config.from_object (dict storage)."""
    value = current_app.config.get(key, default)
    return value if value is not None else default


def _model_label() -> str:
    arn = _cfg_get("BEDROCK_MODEL_ARN")
    if "/" in arn:
        return arn.rsplit("/", 1)[-1]
    return "Bedrock model"


def _execution_mode_hint(mode: str | None = None) -> str:
    """Human-readable backend label for UI — never claim Agent if KB path was used."""
    cfg = _app_config()
    if mode == "local" or not cfg.USE_BEDROCK:
        return "Local fallback"
    if cfg.RAG_BACKEND == "retrieve_and_generate":
        return "Direct Bedrock KB"
    return "Bedrock Agent"


def _notification_settings() -> dict:
    import os

    sms_status = check_sms_account_ready_cached(
        phone=os.environ.get("PITER_DEMO_SMS_RECIPIENT", "").strip() or None,
    )
    mode = os.environ.get("PITER_NOTIFICATION_MODE", "preview").strip().lower()
    live = live_dispatch_enabled()
    email_ready = email_configured()
    allowlist = allowlist_count()
    email_recipients = resolve_demo_recipients("email")
    return {
        "mode": mode,
        "require_confirmation": os.environ.get("PITER_NOTIFICATION_REQUIRE_CONFIRMATION", "true").lower()
        in {"true", "1", "yes"},
        "max_sends_per_incident": int(os.environ.get("PITER_NOTIFICATION_MAX_SENDS_PER_INCIDENT", "1") or 1),
        "live_dispatch_enabled": live,
        "dispatch_ready": live and mode == "live" and email_ready and allowlist > 0,
        "sms_configured": sms_configured(),
        "sms_delivery_ready": bool(sms_status.get("ready")),
        "sms_delivery_message": sms_status.get("message"),
        "sms_console_url": sms_status.get("console_url"),
        "sms_billing_url": sms_status.get("billing_url"),
        "email_configured": email_configured(),
        "allowlist_count": allowlist_count(),
        "demo_sms_configured": bool(os.environ.get("PITER_DEMO_SMS_RECIPIENT", "").strip()),
        "demo_whatsapp_configured": whatsapp_configured(),
        "whatsapp_configured": whatsapp_configured(),
        "demo_email_configured": bool(os.environ.get("PITER_DEMO_EMAIL_RECIPIENT", "").strip()),
        "email_recipients": email_recipients,
        "email_recipients_count": len(email_recipients),
    }


def _bootstrap_context() -> dict:
    max_bytes = current_app.config.get("MAX_UPLOAD_BYTES", 5_242_880)
    if not isinstance(max_bytes, int):
        max_bytes = int(max_bytes or 5_242_880)
    return {
        "examples": flat_example_questions(),
        "example_groups": grouped_example_questions(),
        "max_len": MAX_QUESTION_LEN,
        "model_label": _model_label(),
        "kb_id": _cfg_get("BEDROCK_KB_ID"),
        "s3_bucket": _cfg_get("S3_BUCKET"),
        "s3_prefix": _cfg_get("S3_PREFIX"),
        "max_upload_mb": max(1, max_bytes // (1024 * 1024)),
        "allowed_types": sorted(ALLOWED_UPLOAD_SUFFIXES),
        "sync_kb_default": bool(_cfg_get("BEDROCK_DATA_SOURCE_ID")),
        "spa_enabled": spa_enabled(),
        "use_bedrock": _app_config().USE_BEDROCK,
        "rag_backend": _app_config().RAG_BACKEND,
        "execution_mode_hint": _execution_mode_hint(),
        "notification": _notification_settings(),
        "alert_stream": summarize_alert_stream(),
    }


def _handle_ask(
    question: str,
    *,
    session_id: str | None = None,
    session_attributes: dict[str, str] | None = None,
    prompt_session_attributes: dict[str, str] | None = None,
) -> RagAnswer:
    question = validate_question(question)
    client = _client()

    def _invoke(target: RagClient) -> RagAnswer:
        if session_attributes is not None and hasattr(target, "ask"):
            try:
                return target.ask(
                    question,
                    session_id=session_id,
                    session_attributes=session_attributes,
                    prompt_session_attributes=prompt_session_attributes,
                )
            except TypeError:
                # Backend without session-attribute support (e.g. local client).
                return target.ask(question, session_id=session_id)
        return target.ask(question, session_id=session_id)

    try:
        return _invoke(client)
    except BedrockError as exc:
        if exc.code in _VALIDATION_CODES or not _fallback_enabled():
            raise
        log.warning("Bedrock failed (%s) — answering from LOCAL knowledge base", exc.code)
        local = _invoke(_local_client())
        return replace(local, fallback_used=True, mode="local_fallback")


@bp.get("/api/bootstrap")
def api_bootstrap():
    payload = _bootstrap_context()
    payload["csrf_token"] = generate_csrf()
    return jsonify(ok=True, **payload), 200


_LEGACY_ARCHIVED_MSG = (
    "Legacy HTMX path archived. Use the React SPA and /api/chat or /api/triage."
)


@bp.get("/")
def index():
    if spa_enabled():
        return send_from_directory(_SPA_ROOT, "index.html")
    return (
        jsonify(
            ok=False,
            reason="spa_not_built",
            message="SPA not built. Run: cd frontend && npm run build",
        ),
        503,
    )


@bp.get("/ask")
def ask_get_not_allowed():
    return jsonify(ok=False, message="Method not allowed. Use POST /api/chat."), 405


@bp.post("/ask")
def ask():
    return jsonify(ok=False, reason="legacy_archived", message=_LEGACY_ARCHIVED_MSG), 410


@bp.post("/workflow/triage")
def workflow_triage():
    return jsonify(ok=False, reason="legacy_archived", message=_LEGACY_ARCHIVED_MSG), 410


@bp.post("/api/workflow/triage")
def api_workflow_triage():
    return jsonify(ok=False, reason="legacy_archived", message=_LEGACY_ARCHIVED_MSG), 410


@bp.get("/console")
def console():
    """Legacy console path — redirect to SPA when built."""
    from flask import redirect

    if spa_enabled():
        return redirect("/")
    return jsonify(ok=False, reason="spa_not_built", message=_LEGACY_ARCHIVED_MSG), 503


@bp.get("/api/alert-stream")
def api_alert_stream():
    """Return deterministic alert storm metadata and optional row payload."""
    summary = summarize_alert_stream()
    include_rows = request.args.get("include_rows", "").lower() in {"1", "true", "yes"}
    active_only = request.args.get("active", "").lower() in {"1", "true", "yes"}
    payload: dict = {"ok": True, **summary}
    if active_only:
        payload["rows"] = load_active_alerts()
        payload["active_only"] = True
    elif include_rows:
        payload["rows"] = load_alert_stream()
    return jsonify(payload), 200


@bp.get("/api/kb/manifest")
def api_kb_manifest():
    """List Knowledge Base documents with metadata for the SPA."""
    return jsonify(ok=True, documents=load_kb_manifest(), sections=kb_sections()), 200


def _alert_from_session(session_id: str) -> dict[str, Any] | None:
    """Load alert context stored during triage for Bedrock Agent session attributes."""
    session = session_memory.get_session(session_id)
    if not session:
        return None
    alert = session.get("alert")
    if isinstance(alert, dict) and alert:
        return alert
    card = session.get("triage_card") or {}
    if isinstance(card, dict):
        nested = card.get("alert")
        if isinstance(nested, dict) and nested:
            return nested
    return None


def _ask_fn_for_alert(
    alert: dict[str, Any],
    *,
    triage_complete: str = "false",
):
    """Ask Bedrock Agent with alert-scoped session attributes (KB + action groups)."""
    session_attrs, prompt_attrs = build_session_attributes(
        alert_id=str(alert.get("alert_id") or ""),
        service=str(alert.get("service") or ""),
        environment=str(alert.get("environment") or ""),
        severity=str(alert.get("severity") or ""),
        symptom=str(alert.get("symptom") or alert.get("description") or ""),
        alert_time=str(alert.get("alert_time") or ""),
        triage_complete=triage_complete,
    )

    def ask(question: str, *, session_id: str | None = None) -> RagAnswer:
        return _handle_ask(
            question,
            session_id=session_id,
            session_attributes=session_attrs,
            prompt_session_attributes=prompt_attrs,
        )

    return ask


def _ask_fn_for_session(session_id: str):
    """Follow-up/chat path: reuse stored alert and mark triage complete for the agent."""
    alert = _alert_from_session(session_id) or {}
    return _ask_fn_for_alert(alert, triage_complete="true")


def _api_triage_response(body: dict):
    session_id = body.get("session_id")
    if session_id is not None:
        session_id = str(session_id).strip() or None
    alert = {
        "alert_id": str(body.get("alert_id") or "").strip() or None,
        "service": str(body.get("service", "")).strip(),
        "environment": str(body.get("environment", "")).strip(),
        "severity": str(body.get("severity", "")).strip(),
        "symptom": str(body.get("symptom") or body.get("description") or "").strip(),
        "description": str(body.get("description") or body.get("symptom") or "").strip(),
        "alert_time": str(body.get("alert_time", "")).strip(),
        "duration_minutes": body.get("duration_minutes", 60),
    }
    if not alert["service"] or not alert["symptom"]:
        return jsonify(
            ok=False,
            reason="invalid_alert",
            message="An alert needs at least a service and a symptom/description.",
        ), 400
    try:
        card = run_triage(alert, ask_fn=_ask_fn_for_triage(), session_id=session_id)
    except BedrockError as exc:
        status = 400 if exc.code in _VALIDATION_CODES else 502
        return jsonify(ok=False, reason=exc.code, message=exc.user_message), status
    card.setdefault(
        "tool_results",
        [
            {
                "name": "get_recent_deployments",
                "result": {
                    "suspect_deployment": card.get("suspect_deployment"),
                    "deployments": card.get("suspect_deploys", []),
                    "reason": card.get("deployment_reason", ""),
                },
            },
            {"name": "get_service_context", "result": card.get("owner", {})},
            {"name": "find_similar_incidents", "result": card.get("similar_incidents", [])},
            {"name": "get_escalation_recommendation", "result": card.get("escalation_policy", {})},
        ],
    )
    impact = card.get("impact")
    if isinstance(impact, dict) and impact.get("business_explanation"):
        card.setdefault("business_impact", impact["business_explanation"])
    normalized = normalize_api_response(card)
    sid = normalized.get("session_id")
    if sid:
        summary = (
            f"Triage complete for {alert.get('service', 'service')}: "
            f"priority {normalized.get('priority', 'unknown')}"
        )
        append_turn(
            session_id=str(sid),
            question=f"Analyse alert {alert.get('alert_id') or alert.get('service', '')}",
            answer=summary,
            mode=normalized.get("mode"),
        )
    return jsonify(ok=True, **normalized), 200


@bp.get("/api/demo-alert")
def api_demo_alert():
    """Return the canned demo alert (P1 bet-service storm trigger, GIB-UKGC)."""
    return jsonify(ok=True, alert=get_demo_alert()), 200


@bp.post("/api/triage")
def api_triage():
    """Run triage for a free-form alert and return one triage card."""
    body = request.get_json(silent=True) or {}
    return _api_triage_response(body)


@bp.post("/api/incidents/analyze")
def api_incidents_analyze():
    """Canonical incident analysis endpoint for the React/API demo contract."""
    body = request.get_json(silent=True) or {}
    return _api_triage_response(body)


@bp.post("/api/incident/analyze")
def api_incident_analyze():
    """Alias for reviewers expecting singular /api/incident/analyze."""
    body = request.get_json(silent=True) or {}
    return _api_triage_response(body)


@bp.get("/api/investigations")
def api_investigations():
    """Investigation cards derived from the live alert stream (no static UI data)."""
    limit = request.args.get("limit", "12")
    try:
        cap = max(1, min(50, int(limit)))
    except (TypeError, ValueError):
        cap = 12
    payload = build_investigations(limit=cap)
    overrides = all_statuses()
    if overrides:
        for card in payload.get("investigations", []):
            override = overrides.get(str(card.get("id")))
            if override:
                card["operator_status"] = override
    return jsonify(ok=True, **payload), 200


@bp.post("/api/incidents/<incident_id>/status")
def api_incident_status(incident_id: str):
    """Persist an operator status change (open / in_process / resolved / escalated)."""
    body = request.get_json(silent=True) or {}
    result = set_status(incident_id, str(body.get("status") or ""))
    if result.get("error"):
        return jsonify(ok=False, error=result["error"]), 400
    return jsonify(ok=True, **result), 200


@bp.get("/api/metrics/recent-deployments")
def api_metrics_recent_deployments():
    result = recent_deployments_metrics(
        service=request.args.get("service", ""),
        environment=request.args.get("environment", ""),
        alert_time=request.args.get("alert_time", ""),
        lookback_hours=request.args.get("lookback_hours"),
    )
    status = 400 if result.get("error") else 200
    return jsonify(ok=not result.get("error"), **result), status


@bp.get("/api/metrics/service-context")
def api_metrics_service_context():
    result = service_context_metrics(
        service=request.args.get("service", ""),
        environment=request.args.get("environment", ""),
        severity=request.args.get("severity"),
    )
    status = 400 if result.get("error") else 200
    return jsonify(ok=not result.get("error"), **result), status


@bp.get("/api/metrics/similar-incidents")
def api_metrics_similar_incidents():
    result = similar_incidents_metrics(
        service=request.args.get("service", ""),
        symptom=request.args.get("symptom", ""),
        environment=request.args.get("environment"),
        limit=request.args.get("limit"),
    )
    status = 400 if result.get("error") else 200
    return jsonify(ok=not result.get("error"), **result), status


@bp.get("/api/metrics/escalation-preview")
def api_metrics_escalation_preview():
    result = escalation_preview_metrics(
        service=request.args.get("service", ""),
        severity=request.args.get("severity"),
        business_impact=request.args.get("business_impact"),
    )
    status = 400 if result.get("error") else 200
    return jsonify(ok=not result.get("error"), **result), status


@bp.get("/api/metrics/business-impact")
def api_metrics_business_impact():
    result = business_impact_metrics(
        service=request.args.get("service", ""),
        environment=request.args.get("environment", ""),
        severity=request.args.get("severity", ""),
        duration_minutes=request.args.get("duration_minutes"),
    )
    status = 400 if result.get("error") else 200
    return jsonify(ok=not result.get("error"), **result), status


@bp.get("/api/tools/status")
def api_tools_status():
    """Report readiness of the four required enrichment tools."""
    status = build_tools_status()
    return jsonify(ok=True, **status), 200


@bp.get("/api/history")
def api_history_get():
    """Return saved chat messages for the default or requested demo session."""
    session_id = str(request.args.get("session_id") or "").strip() or None
    return jsonify(ok=True, **get_messages(session_id)), 200


@bp.delete("/api/history")
def api_history_delete():
    """Clear chat history for the default or requested demo session."""
    body = request.get_json(silent=True) or {}
    session_id = str(body.get("session_id") or request.args.get("session_id") or "").strip() or None
    return jsonify(ok=True, **clear_history(session_id)), 200


def _chat_json_response(
    question: str,
    payload: dict[str, Any],
    *,
    session_id: str | None,
) -> tuple[Any, int]:
    memory_session = session_id or str(payload.get("session_id") or "demo-default")
    payload.setdefault("session_id", memory_session)
    normalized = normalize_api_response(payload)
    append_turn(
        session_id=session_id,
        question=question,
        answer=str(normalized.get("answer") or ""),
        mode=normalized.get("mode"),
    )
    out = dict(normalized)
    out["memory"] = {"last_question": question, "session_id": memory_session}
    return jsonify(ok=True, **out), 200


@bp.post("/api/chat")
def api_chat():
    """Canonical chat endpoint with optional incident-session follow-up memory."""
    body = request.get_json(silent=True) or {}
    question = str(body.get("message") or body.get("question") or "").strip()
    session_id = str(body.get("session_id") or "").strip() or None
    if not question:
        return jsonify(ok=False, reason="empty_question", message="Please enter a message."), 400
    if len(question) > MAX_QUESTION_LEN:
        return (
            jsonify(
                ok=False,
                reason="oversize_question",
                message=f"Message is too long ({len(question)} chars). Maximum is {MAX_QUESTION_LEN}.",
            ),
            400,
        )

    structured = structured_chat_reply(question)
    if structured:
        return _chat_json_response(question, dict(structured), session_id=session_id)

    canned = small_talk_reply(question)
    if canned:
        return _chat_json_response(
            question,
            {
                "answer": canned,
                "mode": "local",
                "fallback_used": False,
                "grounded": False,
                "citations": [],
                "recommended_followups": [
                    "What's the last P1 alert?",
                    "Which service is the noisiest?",
                    "What was the last deployment?",
                ],
            },
            session_id=session_id,
        )

    try:
        if session_id:
            follow_up = run_follow_up(
                session_id, question, ask_fn=_ask_fn_for_session(session_id)
            )
            if follow_up is not None:
                return _chat_json_response(question, follow_up, session_id=session_id)
        result = _handle_ask(validate_question(question), session_id=session_id)
    except BedrockError as exc:
        status = 400 if exc.code in _VALIDATION_CODES else 502
        return jsonify(
            ok=False,
            reason=exc.code,
            message=exc.user_message,
            error=exc.code,
            mode="bedrock",
            fallback_used=False,
        ), status

    return _chat_json_response(question, result.to_dict(), session_id=session_id)


@bp.post("/api/escalation/notify")
def api_escalation_notify():
    """Trigger live escalation notify for allowlisted demo recipients only."""
    body = request.get_json(silent=True) or {}
    channel = str(body.get("channel") or "").strip().lower()
    if channel not in {"sms", "email", "whatsapp"}:
        return jsonify(
            ok=False,
            reason="invalid_channel",
            message="channel must be sms, email, or whatsapp",
        ), 400

    import os

    incident_id = str(body.get("incident_id") or "INC-DEMO-STORM").strip()
    service = str(body.get("service") or "bet-service").strip()
    severity = str(body.get("severity") or "P1").strip()
    # Token is server-side only — never accept credentials from the browser.
    confirmation_token = os.environ.get("PITER_NOTIFICATION_CONFIRMATION_TOKEN", "").strip()
    if not confirmation_token:
        return jsonify(
            ok=False,
            reason="server_token_unconfigured",
            message="Live dispatch is not configured on the server (missing confirmation token).",
        ), 503

    message = str(body.get("message") or "").strip() or None
    idempotency_key = str(body.get("idempotency_key") or "").strip() or None
    escalation_context = body.get("escalation_context")
    if escalation_context is not None and not isinstance(escalation_context, dict):
        escalation_context = None

    try:
        result = notify_demo_channel(
            channel=channel,
            incident_id=incident_id,
            service=service,
            severity=severity,
            confirmation_token=confirmation_token,
            message=message,
            escalation_context=escalation_context,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        return jsonify(ok=False, reason="invalid_channel", message=str(exc)), 400

    http_status = int(result.pop("http_status", 502))
    sent = bool(result.get("sent"))
    ok = sent and http_status == 200
    reasons = result.get("reasons")
    if isinstance(reasons, list) and reasons and not result.get("message"):
        result["message"] = "; ".join(str(item) for item in reasons)
    # The dispatch result may already carry its own "ok"; drop it so it does not
    # collide with the explicit ok= keyword passed to jsonify().
    result.pop("ok", None)
    if "error" in result and not sent:
        return jsonify(ok=False, **result), http_status if http_status >= 400 else 400
    if not sent and http_status >= 400:
        return jsonify(ok=False, **result), http_status
    return jsonify(ok=ok, **result), http_status


@bp.post("/api/follow-up")
def api_follow_up():
    """Answer a follow-up question reusing the incident session memory."""
    body = request.get_json(silent=True) or {}
    session_id = str(body.get("session_id") or "").strip()
    question = str(body.get("question") or "").strip()
    if not session_id:
        return jsonify(ok=False, reason="missing_session",
                       message="A follow-up needs the session_id from the triage card."), 400
    if not question:
        return jsonify(ok=False, reason="empty_question", message="Please enter a follow-up question."), 400
    if len(question) > MAX_QUESTION_LEN:
        return (
            jsonify(
                ok=False,
                reason="oversize_question",
                message=f"Question is too long ({len(question)} chars). Maximum is {MAX_QUESTION_LEN}.",
            ),
            400,
        )

    structured = structured_chat_reply(question)
    if structured:
        return _chat_json_response(question, dict(structured), session_id=session_id)

    try:
        result = run_follow_up(session_id, question, ask_fn=_ask_fn_for_session(session_id))
    except BedrockError as exc:
        status = 400 if exc.code in _VALIDATION_CODES else 502
        return jsonify(ok=False, reason=exc.code, message=exc.user_message), status
    if result is None:
        try:
            rag = _handle_ask(validate_question(question))
            payload = rag.to_dict()
            payload["memory_used"] = False
            payload["kind"] = "general"
            payload["session_id"] = session_id
            payload["memory"] = {"last_question": question, "session_id": session_id}
            normalized = normalize_api_response(payload)
            append_turn(
                session_id=session_id,
                question=question,
                answer=str(normalized.get("answer") or ""),
                mode=normalized.get("mode"),
            )
            return jsonify(ok=True, **normalized), 200
        except BedrockError as exc:
            status = 400 if exc.code in _VALIDATION_CODES else 502
            return jsonify(ok=False, reason=exc.code, message=exc.user_message), status
    return _chat_json_response(question, result, session_id=session_id)


@bp.get("/api/incidents/history")
def api_incidents_history():
    """List persisted triage sessions (newest first)."""
    limit = request.args.get("limit", "50")
    try:
        cap = max(1, min(200, int(limit)))
    except (TypeError, ValueError):
        cap = 50
    items = session_memory.list_sessions(limit=cap)
    return jsonify(ok=True, investigations=items, count=len(items)), 200


@bp.get("/api/incidents/history/<session_id>")
def api_incident_history_detail(session_id: str):
    """Full investigation detail for one session."""
    detail = session_memory.get_incident_detail(session_id)
    if detail is None:
        return jsonify(
            ok=False,
            reason="unknown_session",
            message="That incident session was not found. Run triage first.",
        ), 404
    return jsonify(ok=True, **detail), 200


@bp.post("/api/incidents/history/<session_id>/post-mortem")
def api_incident_post_mortem(session_id: str):
    """Persist a post-mortem draft for an incident session."""
    body = request.get_json(silent=True) or {}
    draft = str(body.get("draft") or body.get("post_mortem_draft") or "").strip()
    if not draft:
        return jsonify(
            ok=False,
            reason="empty_draft",
            message="Post-mortem draft text is required.",
        ), 400
    if not session_memory.save_post_mortem_draft(session_id, draft):
        return jsonify(
            ok=False,
            reason="unknown_session",
            message="That incident session was not found. Run triage first.",
        ), 404
    return jsonify(ok=True, session_id=session_id, post_mortem_draft=draft), 200


@bp.get("/api/sessions/<session_id>/history")
def api_session_history(session_id: str):
    """Return saved chat history and triage context for one incident session."""
    history = session_memory.get_history(session_id)
    if history is None:
        return jsonify(
            ok=False,
            reason="unknown_session",
            message="That incident session was not found. Run triage first.",
        ), 404
    return jsonify(ok=True, **history), 200


@bp.get("/api/health")
def api_health():
    """Canonical API health endpoint used by Docker, frontend, and reviewers."""
    return health()


@bp.get("/health")
def health():
    if request.args.get("deep") != "1":
        return jsonify(status="ok"), 200

    checks: dict[str, str] = {"app": "ok"}
    bucket = _cfg_get("S3_BUCKET")
    kb_id = _cfg_get("BEDROCK_KB_ID")
    model_arn = _cfg_get("BEDROCK_MODEL_ARN")

    if not bucket:
        checks["s3"] = "missing_config"
    else:
        checks["s3"] = "configured"

    cfg = _app_config()
    agent_id = _cfg_get("BEDROCK_AGENT_ID") or getattr(cfg, "BEDROCK_AGENT_ID", "")
    agent_alias = _cfg_get("BEDROCK_AGENT_ALIAS_ID") or getattr(cfg, "BEDROCK_AGENT_ALIAS_ID", "")
    if not kb_id or not model_arn:
        checks["bedrock"] = "missing_config"
    else:
        checks["bedrock"] = "configured"
    if cfg.USE_BEDROCK and cfg.RAG_BACKEND == "agent":
        checks["bedrock_agent_configured"] = (
            "configured" if agent_id and agent_alias else "missing_config"
        )
    else:
        checks["bedrock_agent_configured"] = "not_required"

    mem_path = session_memory.store_path()
    try:
        mem_path.parent.mkdir(parents=True, exist_ok=True)
        probe = mem_path.parent / ".health_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks["memory_writable"] = "ok"
    except OSError:
        checks["memory_writable"] = "error"

    try:
        tools = build_tools_status()
        checks["tools_ok"] = "ok" if tools.get("all_ready") else "degraded"
    except Exception:
        checks["tools_ok"] = "error"

    ok_values = {"ok", "configured", "not_required"}
    status = "ok" if all(v in ok_values for v in checks.values()) else "degraded"
    return jsonify(status=status, checks=checks), 200


_UPLOAD_VALIDATION_CODES = {
    "missing_file",
    "unsupported_type",
    "empty_file",
    "file_too_large",
    "upload_disabled",
}


@bp.post("/documents/upload")
def upload_document():
    upload_file = request.files.get("document")
    sync_kb = request.form.get("sync_kb") == "on" or request.form.get("sync_kb") == "true"
    filename = upload_file.filename if upload_file else None
    body = upload_file.read() if upload_file else b""

    try:
        result = _upload_service().upload(filename, body, sync_kb=sync_kb)
    except BedrockError as exc:
        status = 400 if exc.code in _UPLOAD_VALIDATION_CODES else 502
        return jsonify(ok=False, reason=exc.code, message=exc.user_message), status

    payload = {"ok": True, **result.to_dict()}
    if result.sync_warning:
        payload["message"] = result.sync_warning
        return jsonify(**payload), 202

    return jsonify(**payload), 200
