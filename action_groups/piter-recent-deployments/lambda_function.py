"""PITER Lambda: recent deployments, correlation, and rollback availability."""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

_ag_dir = Path(__file__).resolve().parent
for _path in (_ag_dir, _ag_dir.parent):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
from lambda_root import ensure_project_root  # noqa: E402

ensure_project_root()
from app.enrichment_tools import correlate_deployments  # noqa: E402


def _params(event: dict) -> dict[str, str]:
    return {item["name"]: item["value"] for item in event.get("parameters", [])}


def _respond(event: dict, status: int, body: dict) -> dict:
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", "piter-recent-deployments"),
            "apiPath": event.get("apiPath", "/correlate"),
            "httpMethod": event.get("httpMethod", "GET"),
            "httpStatusCode": status,
            "responseBody": {"application/json": {"body": json.dumps(body)}},
        },
        "sessionAttributes": event.get("sessionAttributes", {}),
        "promptSessionAttributes": event.get("promptSessionAttributes", {}),
    }


def _safe_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def lambda_handler(event, context):
    params = _params(event)
    service = params.get("service", "")
    environment = params.get("environment", "")
    alert_time = params.get("alert_time", "")
    log.info(
        "correlate_deployments service=%s environment=%s alert_time=%s",
        service,
        environment,
        alert_time,
    )
    if not all([service, environment, alert_time]):
        return _respond(event, 400, {"error": "service, environment, and alert_time are required"})
    result = correlate_deployments(
        service=service,
        environment=environment,
        alert_time=alert_time,
        lookback_hours=_safe_int(params.get("lookback_hours"), 6),
    )
    return _respond(event, 400 if "error" in result else 200, result)
