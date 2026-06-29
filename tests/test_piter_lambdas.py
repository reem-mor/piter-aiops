"""Tests for the final PITER Lambda responsibility map and notification safety."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION_GROUPS = ROOT / "action_groups"
FINAL_LAMBDAS = {
    "piter-recent-deployments",
    "piter-service-context",
    "piter-similar-incidents",
    "piter-escalation",
}


def _load_lambda(name: str):
    path = ACTION_GROUPS / name / "lambda_function.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _event(name: str, *, params: dict[str, str] | None = None, operation: str | None = None) -> dict:
    items = [{"name": key, "type": "string", "value": value} for key, value in (params or {}).items()]
    if operation:
        items.append({"name": "operation", "type": "string", "value": operation})
    return {
        "messageVersion": "1.0",
        "actionGroup": name,
        "apiPath": "/escalation" if name == "piter-escalation" else "/test",
        "httpMethod": "POST",
        "parameters": items,
        "sessionAttributes": {},
        "promptSessionAttributes": {},
    }


def _body(response: dict) -> dict:
    raw = response["response"]["responseBody"]["application/json"]["body"]
    return json.loads(raw)


def test_final_lambda_source_directories_are_present():
    assert FINAL_LAMBDAS <= {path.name for path in ACTION_GROUPS.iterdir() if path.is_dir()}
    for name in FINAL_LAMBDAS:
        assert (ACTION_GROUPS / name / "lambda_function.py").is_file()
        assert (ACTION_GROUPS / name / "openapi_schema.yaml").is_file()


def test_escalation_preview_valid_input():
    mod = _load_lambda("piter-escalation")
    response = mod.lambda_handler(
        _event(
            "piter-escalation",
            operation="preview",
            params={
                "service": "wallet-service",
                "severity": "P1",
                "incident_id": "INC-1",
                "recipient": "role-primary-oncall",
            },
        ),
        None,
    )
    assert response["response"]["httpStatusCode"] == 200
    data = _body(response)
    assert data["mode"] == "preview"
    assert data["escalation"]["recipient"] == "ro***ll"


def test_escalation_missing_input_and_unknown_operation():
    mod = _load_lambda("piter-escalation")
    missing = mod.lambda_handler(_event("piter-escalation", operation="preview"), None)
    assert missing["response"]["httpStatusCode"] == 400

    unknown = mod.lambda_handler(
        _event(
            "piter-escalation",
            operation="page_everyone",
            params={"service": "wallet-service", "severity": "P1", "incident_id": "INC-1"},
        ),
        None,
    )
    assert unknown["response"]["httpStatusCode"] == 404


def test_escalation_mock_notification_masks_and_does_not_send():
    mod = _load_lambda("piter-escalation")
    response = mod.lambda_handler(
        _event(
            "piter-escalation",
            operation="mock_notify",
            params={
                "service": "wallet-service",
                "severity": "P1",
                "incident_id": "INC-1",
                "recipient": "role-primary-oncall",
                "message": "Escalation preview only",
            },
        ),
        None,
    )
    data = _body(response)
    assert response["response"]["httpStatusCode"] == 200
    assert data["mode"] == "mock"
    assert data["sent"] is False
    assert data["recipient"] == "ro***ll"


def test_escalation_live_blocked_without_required_safety_gates(monkeypatch):
    mod = _load_lambda("piter-escalation")
    monkeypatch.setenv("PITER_NOTIFICATION_MODE", "mock")
    response = mod.lambda_handler(
        _event(
            "piter-escalation",
            operation="live_notify",
            params={
                "service": "wallet-service",
                "severity": "P1",
                "incident_id": "INC-1",
                "recipient": "role-primary-oncall",
                "message": "Escalation preview only",
                "confirmation_token": "bad",
            },
        ),
        None,
    )
    data = _body(response)
    assert response["response"]["httpStatusCode"] == 403
    assert data["blocked"] is True
    assert data["sent"] is False
    assert "PITER_NOTIFICATION_MODE is not live" in data["reasons"]


def test_escalation_live_confirmed_blocked_without_enable_flag(monkeypatch):
    mod = _load_lambda("piter-escalation")
    mod.SENT_IDEMPOTENCY_KEYS.clear()
    monkeypatch.setenv("PITER_NOTIFICATION_MODE", "live")
    monkeypatch.setenv("PITER_NOTIFICATION_REQUIRE_CONFIRMATION", "true")
    monkeypatch.setenv("PITER_NOTIFICATION_CONFIRMATION_TOKEN", "token-ok")
    monkeypatch.setenv("PITER_NOTIFICATION_ALLOWLIST", "role-primary-oncall")
    monkeypatch.setenv("PITER_NOTIFICATION_ALLOWED_SEVERITIES", "P1")
    monkeypatch.delenv("PITER_ENABLE_LIVE_DISPATCH", raising=False)

    event = _event(
        "piter-escalation",
        operation="live_notify",
        params={
            "service": "wallet-service",
            "severity": "P1",
            "incident_id": "INC-1",
            "recipient": "role-primary-oncall",
            "message": "Escalation preview only",
            "confirmation_token": "token-ok",
            "idempotency_key": "INC-1:primary",
        },
    )
    first = mod.lambda_handler(event, None)
    first_data = _body(first)
    assert first["response"]["httpStatusCode"] == 403
    assert first_data["blocked"] is True
    assert first_data["sent"] is False
    assert "PITER_ENABLE_LIVE_DISPATCH is not true" in first_data["reasons"]


def test_escalation_live_dispatches_email_when_enabled(monkeypatch):
    from unittest.mock import MagicMock, patch

    mod = _load_lambda("piter-escalation")
    mod.SENT_IDEMPOTENCY_KEYS.clear()
    monkeypatch.setenv("PITER_NOTIFICATION_MODE", "live")
    monkeypatch.setenv("PITER_ENABLE_LIVE_DISPATCH", "true")
    monkeypatch.setenv("PITER_NOTIFICATION_REQUIRE_CONFIRMATION", "true")
    monkeypatch.setenv("PITER_NOTIFICATION_CONFIRMATION_TOKEN", "token-ok")
    monkeypatch.setenv("PITER_NOTIFICATION_ALLOWLIST", "ops@example.com")
    monkeypatch.setenv("PITER_NOTIFICATION_ALLOWED_SEVERITIES", "P1")
    monkeypatch.setenv("PITER_SES_SENDER_EMAIL", "noreply@example.com")

    event = _event(
        "piter-escalation",
        operation="live_notify",
        params={
            "service": "wallet-service",
            "severity": "P1",
            "incident_id": "INC-1",
            "recipient": "ops@example.com",
            "message": "Escalation live test",
            "confirmation_token": "token-ok",
            "idempotency_key": "INC-1:email",
        },
    )

    mock_ses = MagicMock()
    mock_ses.send_email.return_value = {"MessageId": "msg-123"}

    with patch("app.services.notification_dispatch.boto3.client", return_value=mock_ses):
        first = mod.lambda_handler(event, None)
    first_data = _body(first)
    assert first["response"]["httpStatusCode"] == 200
    assert first_data["mode"] == "live"
    assert first_data["sent"] is True
    assert first_data["message_id"] == "msg-123"

    second = mod.lambda_handler(event, None)
    second_data = _body(second)
    assert second["response"]["httpStatusCode"] == 403
    assert "message was already sent" in second_data["reasons"]
