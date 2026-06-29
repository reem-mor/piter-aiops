"""Minimal, dependency-free MCP server for PITER AiOps (stdio transport).

Implements the JSON-RPC 2.0 subset of the Model Context Protocol needed to expose
the four read-only PITER tools to any MCP client:

  - initialize
  - tools/list
  - tools/call
  - notifications/initialized (acknowledged, no reply)

Transport: newline-delimited JSON-RPC messages over stdin/stdout (MCP stdio).

This server is READ-ONLY by design — no AWS, no network, no notifications. It
reuses ``app.enrichment_tools`` so it shares datasets and behaviour with the
Flask app and the Bedrock Action Group Lambdas (single source of truth).

Run:
    python -m mcp.server          # from projects/piter-aiops
or:
    python mcp/server.py

A self-test (no MCP client needed):
    python mcp/server.py --selftest
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from mcp.tools import UnknownToolError, call_tool, list_tools  # noqa: E402

SERVER_NAME = "piter-aiops"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    """Return a JSON-RPC response dict, or None for notifications."""
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    if method == "notifications/initialized":
        return None  # notification, no response

    if method == "tools/list":
        return _result(request_id, {"tools": list_tools()})

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            payload = call_tool(name, arguments)
        except UnknownToolError as exc:
            return _error(request_id, -32601, str(exc))
        except (KeyError, ValueError, TypeError) as exc:  # invalid/missing arguments
            return _error(request_id, -32602, f"invalid arguments: {exc}")
        text = json.dumps(payload, indent=2, default=str)
        return _result(
            request_id,
            {"content": [{"type": "text", "text": text}], "isError": False},
        )

    if request_id is not None:
        return _error(request_id, -32601, f"method not found: {method}")
    return None


def serve(stdin=sys.stdin, stdout=sys.stdout) -> int:
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(message)
        if response is not None:
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()
    return 0


def _selftest() -> int:
    """Exercise the protocol without an MCP client."""
    init = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init and init["result"]["serverInfo"]["name"] == SERVER_NAME
    tools = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {t["name"] for t in tools["result"]["tools"]}
    assert names == {"recent_deployments", "service_context", "similar_incidents", "escalation_preview"}
    call = handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "service_context",
                "arguments": {"service": "postgres", "severity": "P2", "environment": "NJ-DGE"},
            },
        }
    )
    assert call["result"]["isError"] is False
    esc = handle(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "escalation_preview", "arguments": {"service": "postgres", "severity": "P1"}},
        }
    )
    body = json.loads(esc["result"]["content"][0]["text"])
    assert body["sends_notifications"] is False
    print("MCP self-test OK — 4 tools listed, service_context + escalation_preview (no-send) work.")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    raise SystemExit(serve())
