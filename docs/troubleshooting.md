# Troubleshooting

## Empty User Message

`/api/chat` returns `empty_question` with a safe message.

## Unknown Service

Tools return structured `error` fields instead of crashing the backend.

## Missing Data File

Run:

```powershell
python scripts/validate_data.py
```

The script reports the missing CSV/JSON file or column. Canonical runtime data is under `data/source/` — see `docs/data_dictionary.md`.

## Bedrock Unavailable

Set `PITER_USE_BEDROCK=false` for local fallback, or keep `LOCAL_FALLBACK=true` while testing Bedrock.

When Bedrock fails at runtime, API responses include `ok=false`, `mode=bedrock`, and `fallback_used=false` so the UI does not show fake success.

## Missing Agent IDs

For `RAG_BACKEND=agent`, configure:

- `BEDROCK_AGENT_ID`
- `BEDROCK_AGENT_ALIAS_ID`

See `docs/environment.md`.

## Knowledge Base Not Synced

Sync `knowledge_base/` to S3, start ingestion, and test retrieval before the live demo:

```powershell
python scripts/sync_knowledge_base.py --ingest --wait
python scripts/kb_smoke_test.py
```

The canonical S3 prefix is `projects/piter-aiops/knowledge_base/`.

## AWS CLI Pitfalls (PowerShell)

### KB retrieve returns empty results

The data source prefix must match both the S3 sync path **and** the Bedrock KB IAM role `s3:GetObject` scope. If ingestion reports 403 on `projects/piter-aiops/knowledge_base/*`, extend `AmazonBedrockS3PolicyForKnowledgeBase_*` using `infra/kb_s3_policy_patch.json`, then re-run ingestion.

### `ResourceNotFoundException` for `piter-*` Lambdas

Create the functions before updating action groups:

```powershell
.\scripts\aws_deploy_fix.ps1
```

### `add-permission` sourceArn validation error

PowerShell treats `$env:AWS_REGION:$ACCOUNT_ID` as a scoped variable. Build the ARN explicitly:

```powershell
$AgentSourceArn = "arn:aws:bedrock:${env:AWS_REGION}:${AccountId}:agent/${AgentId}"
```

### `create-agent-version` not found

There is no `create-agent-version` AWS CLI command. Either call `update-agent-alias` without `--routing-configuration` to snapshot a new version, or point a test alias at `DRAFT` (`TSTALIASID`).

### `invoke-agent` not in AWS CLI

`bedrock-agent-runtime` in AWS CLI 2.x may not expose `invoke_agent`. Use:

```powershell
py -3.12 scripts/agent_smoke_test.py
```

### Agent rename `ValidationException`

Agent names must match `([0-9a-zA-Z][_-]?){1,100}` — no spaces. Keep the existing name and update instructions only.

### Cannot delete enabled action groups

Disable first with `update-agent-action-group --action-group-state DISABLED`, or repoint the group to the new Lambda with `update-agent-action-group`.

### `Failed to create OpenAPI 3 model` on action group update

Bedrock requires response bodies with `content.application/json.schema`, parameter `description` fields, and API paths that match the Lambda handler defaults (`/correlate`, `/owner`, `/impact`, `/similar`, `/escalation`). Upload schemas to S3 under `agent/piter-*/openapi_schema.yaml` and reference them in `aws_deploy_fix.ps1`.

### Corrected one-shot deploy

```powershell
.\scripts\aws_deploy_fix.ps1
python scripts/sync_knowledge_base.py --ingest --wait
```

## History

- `GET /api/history` returns the current process-local history (optional `session_id` query param).
- `DELETE /api/history` clears history for the default or specified session.
- History resets when the Flask process restarts.

## EC2 demo not reachable

See `docs/ec2_deployment.md`: security group must allow TCP 8080 from your demo audience, instance needs a public IP, and Docker must publish `-p 8080:8080`.
