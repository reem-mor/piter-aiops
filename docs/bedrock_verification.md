# Bedrock verification (read-only)

Run these commands against the configured AWS account. **No mutations** — inspection only.

## Identity

```bash
aws sts get-caller-identity
```

## Agent

```bash
aws bedrock-agent get-agent --agent-id "$BEDROCK_AGENT_ID"
aws bedrock-agent get-agent-alias --agent-id "$BEDROCK_AGENT_ID" --agent-alias-id "$BEDROCK_AGENT_ALIAS_ID"
aws bedrock-agent list-agent-action-groups --agent-id "$BEDROCK_AGENT_ID" --agent-version DRAFT
```

## Knowledge Base

```bash
aws bedrock-agent get-knowledge-base --knowledge-base-id "$BEDROCK_KB_ID"
aws bedrock-agent list-data-sources --knowledge-base-id "$BEDROCK_KB_ID"
```

## Application health (no AWS CLI required)

```bash
curl -s "http://127.0.0.1:8080/api/health?deep=1" | jq .
curl -s "http://127.0.0.1:8080/api/tools/status" | jq .
```

The **AWS / Bedrock** page in the SPA surfaces `bedrockConfigured`, region, agent IDs, KB status, and action-group readiness from these endpoints.

## Source labels

| Mode | UI label |
|------|----------|
| `bedrock_agent` | Source: Bedrock Agent + Knowledge Base |
| `local_fallback` | Source: Local project knowledge base fallback |
| `local` | Source: Local project knowledge base |

Never claim Bedrock grounding when `fallback_used: true` or `mode: local_fallback`.
