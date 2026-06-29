# AWS Sync Guide

## S3

Upload only the focused Knowledge Base corpus:

```powershell
aws s3 sync knowledge_base/ s3://<bucket-name>/projects/piter-aiops/knowledge_base/ --exclude "*.tmp" --exclude "__pycache__/*"
```

Verify:

```powershell
aws s3 ls s3://<bucket-name>/projects/piter-aiops/knowledge_base/ --recursive
```

## Bedrock Knowledge Base

1. Use S3 data source prefix `projects/piter-aiops/knowledge_base/`.
2. Start a sync from the Bedrock console or run `python scripts/sync_knowledge_base.py`.
3. Verify ingestion status is complete.
4. Test retrieval with auth login, deployment rollback, Redis token store, database connectivity, and API Gateway 5xx questions.

## Bedrock Agent

- Agent name: `piter-aiops-incident-response-agent`
- Recommended model: `amazon.nova-lite-v1:0` for cost-effective demo latency.
- Attach the Knowledge Base.
- Add action groups for recent deployments, service context, similar incidents, and escalation preview.
- Prepare the agent after configuration changes.
- Create a new version after prepare succeeds.
- Update the live alias to that version.
- Put the alias ID in `.env` as `BEDROCK_AGENT_ALIAS_ID`.

## Draft, Version, Alias

- Draft is editable.
- Version is immutable after prepare/version creation.
- Alias points runtime traffic to a version.
- Update aliases only after testing the prepared version.

## Action Group / Lambda Mapping

- `mcp/recent_deployments.py` maps to a Lambda action for recent deployment lookup.
- `mcp/service_context.py` maps to service ownership and dependency lookup.
- `mcp/similar_incidents.py` maps to historical incident lookup.
- `mcp/escalation.py` maps to safe escalation preview.

## IAM

Use least privilege for:

- `bedrock-agent-runtime:InvokeAgent`
- Knowledge Base retrieval APIs required by the selected Bedrock flow
- S3 read access to `projects/piter-aiops/knowledge_base/*`
- Lambda invoke permissions for action-group functions
- CloudWatch Logs write permissions for Lambda

Do not use administrator access as the final demo posture.

## Guardrails

- Do not expose secrets.
- Do not send real escalation messages automatically.
- Produce safe escalation previews only.
- Avoid hallucinating production facts.
- State when information is missing.
