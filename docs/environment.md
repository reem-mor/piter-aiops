# PITER AiOps — Environment Variables

Copy [`.env.example`](../.env.example) to `.env` for local Bedrock mode. Never commit `.env`.

## Required for Bedrock Agent mode (`RAG_BACKEND=agent`)

| Variable | Legacy alias | Description |
|----------|--------------|-------------|
| `PITER_AWS_REGION` | `AWS_REGION` | AWS region (e.g. `us-east-1`) |
| `PITER_BEDROCK_KB_ID` | `BEDROCK_KB_ID` | Knowledge Base ID |
| `PITER_BEDROCK_MODEL_ARN` | `BEDROCK_MODEL_ARN` | Foundation model ARN for direct KB RAG |
| `PITER_BEDROCK_AGENT_ID` | `BEDROCK_AGENT_ID` | Bedrock Agent ID |
| `PITER_BEDROCK_AGENT_ALIAS_ID` | `BEDROCK_AGENT_ALIAS_ID` | Prepared agent alias ID |
| `PITER_FLASK_SECRET_KEY` | `FLASK_SECRET_KEY` | Flask session/CSRF secret |

## Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `PITER_USE_BEDROCK` | `true` | Set `false` for offline local RAG |
| `PITER_RAG_BACKEND` | `agent` | `agent` or `retrieve_and_generate` |
| `PITER_MOCK_MODE` | `false` | Force local mode |
| `PITER_BEDROCK_NUM_RESULTS` | `5` | KB retrieval count |
| `PITER_S3_BUCKET` | — | S3 bucket for KB sync / uploads |
| `PITER_S3_PREFIX` | `projects/piter-aiops/knowledge_base` | KB document prefix |
| `PITER_BEDROCK_DATA_SOURCE_ID` | — | KB data source for ingestion jobs |
| `PITER_DOCKER_USE_BEDROCK` | `false` | Opt-in Bedrock inside Docker Compose |
| `PITER_NOTIFICATION_MODE` | `mock` | `mock`, `preview`, or gated `live` |
| `PITER_ENABLE_LIVE_DISPATCH` | `false` | Must be `true` for real SMS/email |

## Local fallback

When Bedrock fails and Flask `LOCAL_FALLBACK` is enabled (default in app config), the API answers from the local TF-IDF index over `knowledge_base/`. Responses include `fallback_used: true` and `mode: local_fallback`.

## Credentials

Use AWS CLI profile (`AWS_PROFILE`) or standard environment credentials. Empty `AWS_PROFILE` is unset automatically to avoid `ProfileNotFound` errors.

See also [`docs/aws_sync_guide.md`](aws_sync_guide.md) and [`docs/ec2_deployment.md`](ec2_deployment.md).
