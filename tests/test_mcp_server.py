"""Tests for the read-only MCP tool layer (mcp/server.py + mcp/tools)."""
from __future__ import annotations

import json

from mcp import server
from mcp.tool_registry import call_registered_tool, list_registered_tools
from mcp.tools import call_tool, list_tools

EXPECTED_TOOLS = {
    "recent_deployments",
    "service_context",
    "similar_incidents",
    "escalation_preview",
}


def test_list_tools_exposes_four_piter_tools():
    names = {t["name"] for t in list_tools()}
    assert names == EXPECTED_TOOLS
    for tool in list_tools():
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"


def test_initialize_handshake():
    resp = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert resp["result"]["serverInfo"]["name"] == "piter-aiops"
    assert resp["result"]["protocolVersion"]


def test_initialized_notification_has_no_response():
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_tools_call_service_context_returns_owner():
    out = call_tool(
        "service_context",
        {"service": "bet-service", "severity": "P2", "environment": "NJ-DGE"},
    )
    assert "owner" in out


def test_escalation_preview_never_sends_and_masks_recipient():
    out = call_tool("escalation_preview", {"service": "bet-service", "severity": "P1"})
    assert out["mode"] == "preview"
    assert out["sends_notifications"] is False
    # masked recipient must not equal a full raw value
    assert "***" in out["recipient_masked"] or out["recipient_masked"] == ""


def test_tools_call_via_protocol_returns_text_content():
    resp = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "similar_incidents",
                "arguments": {"service": "bet-service", "symptom": "CPU above 90%"},
            },
        }
    )
    assert resp["result"]["isError"] is False
    body = json.loads(resp["result"]["content"][0]["text"])
    assert "similar_incidents" in body or "service" in body


def test_unknown_tool_returns_method_not_found_error():
    resp = server.handle(
        {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "nope", "arguments": {}}}
    )
    assert resp["error"]["code"] == -32601


def test_missing_required_argument_returns_invalid_params_error():
    # A known tool invoked without its required arguments must be -32602
    # (invalid params), not -32601 (method not found).
    resp = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "recent_deployments", "arguments": {}},
        }
    )
    assert resp["error"]["code"] == -32602


def test_explicit_piter_tool_registry_exposes_required_names():
    assert list_registered_tools() == [
        "find_similar_incidents",
        "get_escalation_recommendation",
        "get_recent_deployments",
        "get_service_context",
    ]
    out = call_registered_tool("get_service_context", service="auth-service")
    assert out["owner_team"] == "Identity & Access"
