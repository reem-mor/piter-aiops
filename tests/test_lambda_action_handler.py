"""Tests for PITER AiOps Lambda-style action group handlers."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_handler(folder: str):
    path = ROOT / "action_groups" / folder / "lambda_function.py"
    spec = importlib.util.spec_from_file_location(f"{folder}_lambda", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.lambda_handler


def _event(action_group: str, path: str, parameters: dict[str, str]) -> dict:
    return {
        "messageVersion": "1.0",
        "actionGroup": action_group,
        "apiPath": path,
        "httpMethod": "GET",
        "parameters": [
            {"name": key, "type": "string", "value": value}
            for key, value in parameters.items()
        ],
        "sessionAttributes": {},
        "promptSessionAttributes": {},
    }


def _body(resp: dict) -> dict:
    raw = resp["response"]["responseBody"]["application/json"]["body"]
    return json.loads(raw)


def test_recent_deployments_lambda_returns_auth_deployments():
    handler = _load_handler("piter-recent-deployments")
    resp = handler(
        _event(
            "piter-recent-deployments",
            "/correlate",
            {
                "service": "auth-service",
                "environment": "NJ-DGE",
                "alert_time": "2026-06-10T09:00:00Z",
            },
        ),
        None,
    )
    assert resp["response"]["httpStatusCode"] == 200
    assert "deployments" in _body(resp)


def test_service_context_lambda_returns_owner():
    handler = _load_handler("piter-service-context")
    resp = handler(
        _event(
            "piter-service-context",
            "/owner",
            {"service": "auth-service", "environment": "NJ-DGE"},
        ),
        None,
    )
    assert resp["response"]["httpStatusCode"] == 200
    assert _body(resp)["owner_team"] == "Identity & Access"


def test_similar_incidents_lambda_returns_matches():
    handler = _load_handler("piter-similar-incidents")
    resp = handler(
        _event(
            "piter-similar-incidents",
            "/similar",
            {"service": "auth-service", "symptom": "users cannot log in"},
        ),
        None,
    )
    assert resp["response"]["httpStatusCode"] == 200
    assert "similar_incidents" in _body(resp)


def test_escalation_lambda_preview_never_sends():
    handler = _load_handler("piter-escalation")
    resp = handler(
        _event(
            "piter-escalation",
            "/escalation",
            {
                "operation": "preview",
                "service": "auth-service",
                "severity": "P2",
                "incident_id": "INC-DEMO",
                "recipient": "identity-oncall",
            },
        ),
        None,
    )
    body = _body(resp)
    assert resp["response"]["httpStatusCode"] == 200
    assert body["mode"] == "preview"
    assert "recipient" in body["escalation"]
