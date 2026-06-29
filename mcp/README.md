# PITER AiOps MCP Tool Layer

This folder contains the local, read-only MCP-style tool contract for PITER AiOps. It mirrors the production Bedrock Action Group tools without requiring AWS.

## Tools

| Tool | Purpose |
|---|---|
| `get_recent_deployments` | Recent deployment lookup |
| `get_service_context` | Service owner, dependencies, and escalation context |
| `find_similar_incidents` | Historical incident lookup |
| `get_escalation_recommendation` | Safe escalation preview |

The stdio MCP server also exposes compatibility names:

- `recent_deployments`
- `service_context`
- `similar_incidents`
- `escalation_preview`

## Safety

- Read-only.
- No AWS calls.
- No network calls.
- No live escalation sends.
- Escalation output is preview-only.

## Run

```powershell
python -m mcp.server
python mcp/server.py --selftest
```

## Files

- `tool_registry.py`: simple callable registry for tests and demos.
- `recent_deployments.py`: deployment lookup adapter.
- `service_context.py`: ownership/dependency adapter.
- `similar_incidents.py`: historical incident adapter.
- `escalation.py`: safe escalation recommendation adapter.
- `server.py`: dependency-free JSON-RPC stdio server.
