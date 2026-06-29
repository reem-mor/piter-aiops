# Action Groups Setup

Create one action group per tool:

- `piter-recent-deployments` — OpenAPI path `/correlate`
- `piter-service-context` — OpenAPI paths `/owner`, `/impact`
- `piter-similar-incidents` — OpenAPI path `/similar`
- `piter-escalation` — OpenAPI path `/escalation` (preview/mock/gated live)

Each action group exposes a small OpenAPI schema (uploaded to S3) and invokes a Lambda that returns JSON-compatible output.

Local source mapping:

- `mcp/recent_deployments.py`
- `mcp/service_context.py`
- `mcp/similar_incidents.py`
- `mcp/escalation.py`

Deploy/update with:

```powershell
.\scripts\aws_deploy_fix.ps1
```
