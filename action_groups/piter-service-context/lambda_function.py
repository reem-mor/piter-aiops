"""PITER Lambda: service ownership, on-call role, impact, priority, exposure."""
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
from app.enrichment_tools import lookup_owner_and_escalation, score_business_impact  # noqa: E402


def _params(event: dict) -> dict[str, str]:
    return {item["name"]: item["value"] for item in event.get("parameters", [])}


def _respond(event: dict, status: int, body: dict) -> dict:
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", "piter-service-context"),
            "apiPath": event.get("apiPath", "/service-context"),
            "httpMethod": event.get("httpMethod", "GET"),
            "httpStatusCode": status,
            "responseBody": {"application/json": {"body": json.dumps(body)}},
        },
        "sessionAttributes": event.get("sessionAttributes", {}),
        "promptSessionAttributes": event.get("promptSessionAttributes", {}),
    }


def lambda_handler(event, context):
    params = _params(event)
    path = event.get("apiPath", "/owner")
    service = params.get("service", "")
    environment = params.get("environment", "")
    if not service or not environment:
        return _respond(event, 400, {"error": "service and environment are required"})
    log.info("service_context path=%s service=%s environment=%s", path, service, environment)
    if path == "/impact":
        severity = params.get("severity", "")
        if not severity:
            return _respond(event, 400, {"error": "severity is required"})
        result = score_business_impact(service=service, environment=environment, severity=severity)
        if "error" not in result:
            result["impact_tier"] = result.get("impact_tier") or result.get("service_tier", "")
    else:
        result = lookup_owner_and_escalation(
            service=service,
            environment=environment,
            severity=params.get("severity", ""),
        )
        if "error" not in result:
            result["on_call_channel"] = result.get("slack_channel", "")
            result["escalation"] = result.get("escalation_path", "")
    return _respond(event, 400 if "error" in result else 200, result)
