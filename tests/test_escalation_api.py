"""Tests for POST /api/escalation/notify."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
ACTION_GROUPS = ROOT / "action_groups"


def _load_lambda(name: str):
    path = ACTION_GROUPS / name / "lambda_function.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_escalation_notify_requires_channel(client):
    response = client.post("/api/escalation/notify", json={"confirmation_token": "tok"})
    assert response.status_code == 400
    data = response.get_json()
    assert data["ok"] is False
    assert data["reason"] == "invalid_channel"


def test_escalation_notify_requires_server_token(client, monkeypatch):
    monkeypatch.delenv("PITER_NOTIFICATION_CONFIRMATION_TOKEN", raising=False)
    response = client.post(
        "/api/escalation/notify",
        json={"channel": "sms", "incident_id": "INC-1", "service": "bet-service", "severity": "P1"},
    )
    assert response.status_code == 503
    data = response.get_json()
    assert data["reason"] == "server_token_unconfigured"


def test_escalation_notify_unconfigured_recipient_returns_clean_error(client, monkeypatch):
    """Regression: dispatch result carrying its own "ok" must not 500 the route."""
    monkeypatch.setenv("PITER_NOTIFICATION_MODE", "mock")
    monkeypatch.delenv("PITER_ENABLE_LIVE_DISPATCH", raising=False)
    monkeypatch.delenv("PITER_DEMO_EMAIL_RECIPIENT", raising=False)

    monkeypatch.setenv("PITER_NOTIFICATION_CONFIRMATION_TOKEN", "token-ok")
    response = client.post(
        "/api/escalation/notify",
        json={
            "channel": "email",
            "incident_id": "INC-API-ERR",
            "service": "bet-service",
            "severity": "P1",
        },
    )
    assert response.status_code != 500
    assert response.status_code == 400
    data = response.get_json()
    assert data["ok"] is False
    assert data.get("sent") in (False, None)


def test_escalation_notify_blocked_without_live_gates(client, monkeypatch):
    monkeypatch.setenv("PITER_DEMO_SMS_RECIPIENT", "+15551234567")
    monkeypatch.setenv("PITER_NOTIFICATION_MODE", "mock")
    monkeypatch.setenv("PITER_NOTIFICATION_CONFIRMATION_TOKEN", "token-ok")
    monkeypatch.delenv("PITER_ENABLE_LIVE_DISPATCH", raising=False)

    response = client.post(
        "/api/escalation/notify",
        json={
            "channel": "sms",
            "incident_id": "INC-API-1",
            "service": "bet-service",
            "severity": "P1",
        },
    )
    assert response.status_code == 403
    data = response.get_json()
    assert data["sent"] is False
    assert data["blocked"] is True


def test_escalation_notify_succeeds_with_mocked_dispatch(client, monkeypatch):
    mod = _load_lambda("piter-escalation")
    mod.SENT_IDEMPOTENCY_KEYS.clear()

    monkeypatch.setenv("PITER_NOTIFICATION_MODE", "live")
    monkeypatch.setenv("PITER_ENABLE_LIVE_DISPATCH", "true")
    monkeypatch.setenv("PITER_NOTIFICATION_REQUIRE_CONFIRMATION", "true")
    monkeypatch.setenv("PITER_NOTIFICATION_CONFIRMATION_TOKEN", "token-ok")
    monkeypatch.setenv("PITER_NOTIFICATION_ALLOWLIST", "ops@example.com")
    monkeypatch.setenv("PITER_NOTIFICATION_ALLOWED_SEVERITIES", "P1")
    monkeypatch.setenv("PITER_DEMO_EMAIL_RECIPIENT", "ops@example.com")
    monkeypatch.setenv("PITER_SES_SENDER_EMAIL", "noreply@example.com")

    mock_ses = MagicMock()
    mock_ses.send_email.return_value = {"MessageId": "ses-msg-1"}

    with patch("app.services.notification_dispatch.boto3.client", return_value=mock_ses):
        response = client.post(
            "/api/escalation/notify",
            json={
                "channel": "email",
                "incident_id": "INC-API-2",
                "service": "bet-service",
                "severity": "P1",
            },
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["sent"] is True
    assert data["message_id"] == "ses-msg-1"


def test_bootstrap_includes_notification_readiness(client, monkeypatch):
    monkeypatch.setenv("PITER_ENABLE_LIVE_DISPATCH", "true")
    monkeypatch.setenv("PITER_DEMO_SMS_RECIPIENT", "+15551234567")
    monkeypatch.setenv("PITER_SES_SENDER_EMAIL", "noreply@example.com")
    monkeypatch.setattr(
        "app.routes.check_sms_account_ready_cached",
        lambda **kwargs: {"ready": False, "reason": "test_stub"},
    )

    response = client.get("/api/bootstrap")
    assert response.status_code == 200
    data = response.get_json()
    notification = data["notification"]
    assert notification["live_dispatch_enabled"] is True
    assert notification["demo_sms_configured"] is True
    assert notification["email_configured"] is True


def test_bootstrap_dispatch_ready_requires_allowlist(client, monkeypatch):
    monkeypatch.setenv("PITER_NOTIFICATION_MODE", "live")
    monkeypatch.setenv("PITER_ENABLE_LIVE_DISPATCH", "true")
    monkeypatch.setenv("PITER_SES_SENDER_EMAIL", "noreply@example.com")
    monkeypatch.setenv("PITER_NOTIFICATION_ALLOWLIST", "oncall@example.com")

    response = client.get("/api/bootstrap")
    notification = response.get_json()["notification"]
    assert notification["dispatch_ready"] is True
