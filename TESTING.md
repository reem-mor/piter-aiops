# Testing - PITER AiOps

All unit tests run offline with mocked Bedrock, so AWS credentials are not required for normal development. Live Bedrock checks are separate and should be run only when `.env` and the local AWS profile are configured.

## Quick run

```powershell
cd C:\dev\amdocs-ai-course\projects\piter-aiops
py -3.12 -m pip install -r requirements-dev.txt
py -3.12 -m compileall .
py -3.12 -m pytest -q
```

Frontend (SPA served by Flask):

```powershell
cd frontend
npm ci
npm run build
npm run lint
# Output: ../app/static/spa/
```

## Docker smoke test

```powershell
cd C:\dev\amdocs-ai-course\projects\piter-aiops
docker compose up --build -d
Invoke-WebRequest http://localhost:8080/health
# Browser: http://localhost:8080/#live-kb and /#mvp (5 alerts, structured answers)
docker compose down
```

## Live Bedrock (optional)

Requires a valid `.env`, AWS CLI credentials, a prepared Bedrock Agent alias, and an active Knowledge Base:

```powershell
py -3.12 scripts/verify_credentials.py
py -3.12 scripts/agent_smoke_test.py
py -3.12 scripts/verify_live_demo.py
py -3.12 scripts/verify_live_demo.py --base-url http://<ec2-public-dns>:8080
```

After adding corpus files under `knowledge_base/`, sync to S3 and start a Bedrock ingestion job before running smoke tests:

```powershell
py -3.12 scripts/sync_knowledge_base.py --ingest --wait
py -3.12 scripts/kb_smoke_test.py
```

## AWS-marked tests

Tests that call live AWS APIs are tagged `@pytest.mark.aws` and skipped unless `PITER_RUN_AWS_TESTS=1` is set. See `docs/environment.md` for required variables.

## What is covered

| Area | Tests |
|------|--------|
| Answer sections + citation previews | `tests/test_text_utils.py` |
| Severity-based demo impact | `tests/test_workflow_impact.py` |
| 5 workflow alerts + demo questions | `tests/test_data_corpus.py` |
| JSON API shape (`answer_sections`, `piter`, citations) | `tests/test_api_routes.py`, `tests/test_bedrock_client.py` |
| Incident analysis + priority ranking | `tests/test_incident_analysis.py` |
| Chat session history | `tests/test_api_routes.py` |
| Legacy HTMX + SPA routes | `tests/test_routes.py`, `tests/test_spa_mode.py` |
| MCP/tool functions | `tests/test_mcp_server.py`, `tests/test_enrichment_tools.py`, `tests/test_piter_lambdas.py` |
| Lambda action group routing | `tests/test_lambda_action_handler.py` |
| Memory and history | `tests/test_follow_up_triage_alignment.py` |
| Guardrails and fallback behavior | `tests/test_guardrails.py`, `tests/test_rag_factory.py`, `tests/test_bedrock_client.py` |

## Unverified without AWS

- Bedrock Agent alias status and `invoke_agent` event stream
- Bedrock Knowledge Base sync status
- Live Q&A grounding against the synced corpus
- EC2 public URL and IAM instance profile

Check in AWS Console: Knowledge Bases → data source **Available**, model access enabled, Agent alias **Prepared**, and EC2 running for the public demo.
