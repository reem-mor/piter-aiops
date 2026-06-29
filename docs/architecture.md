# PITER AiOps Architecture

PITER AiOps is an incident-response assistant for NOC, DevOps, SRE, and production operations teams.

## Components

- Flask backend exposes health, chat, incident analysis, history, and tool-status APIs.
- React frontend provides the live demo console.
- Amazon Bedrock Agent is invoked through `boto3` when AWS is configured.
- Bedrock Knowledge Base retrieves from the `knowledge_base/` corpus.
- Local fallback uses the same `knowledge_base/` markdown through a TF-IDF retriever.
- MCP-style tools mirror the Bedrock Action Group contracts locally.
- Pandas/CSV/JSON processing validates and powers the data layer.

## Request Flow

1. User asks `/api/chat` or submits `/api/incidents/analyze`.
2. Flask validates input and calls Bedrock Agent when `PITER_USE_BEDROCK=true`.
3. If Bedrock is unavailable and fallback is enabled, Flask uses local RAG.
4. Incident analysis enriches with recent deployments, service context, similar incidents, escalation policy, and business impact.
5. Response is normalized into the required PITER structure.

## Required API Endpoints

- `GET /health`
- `GET /api/health`
- `POST /api/chat`
- `POST /api/incidents/analyze` (alias of triage handler)
- `GET /api/history`
- `DELETE /api/history`
- `GET /api/tools/status`

The React SPA primarily uses `POST /api/triage`, `POST /api/follow-up`, and `POST /ask`. The `/api/chat` and `/api/incidents/analyze` routes remain API-compatible aliases for demos and automated tests.

## Runtime Modes

- Local demo: `PITER_USE_BEDROCK=false`
- Bedrock Agent: `PITER_USE_BEDROCK=true`, `RAG_BACKEND=agent`
- Direct KB fallback: `RAG_BACKEND=retrieve_and_generate`
