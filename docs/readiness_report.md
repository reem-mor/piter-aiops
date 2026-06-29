# PITER AiOps — Readiness Report

Mid-course review against **AI-Augmented Software Engineering** project guidelines and the PITER AiOps implementation plan.

## Requirements Gap Matrix

| Course requirement | Status | Evidence |
|--------------------|--------|----------|
| Flask web application | Met | [`app/routes.py`](../app/routes.py), [`wsgi.py`](../wsgi.py) |
| RAG (document Q&A) | Met | Bedrock KB + [`knowledge_base/`](../knowledge_base/), local TF-IDF in [`app/services/local_rag.py`](../app/services/local_rag.py) |
| MCP / tools | Met | [`mcp/server.py`](../mcp/server.py), four enrichment tools, Bedrock action groups |
| Docker | Met | [`Dockerfile`](../Dockerfile), [`docker-compose.yml`](../docker-compose.yml) |
| Pandas / CSV / JSON | Met | [`app/services/data_access.py`](../app/services/data_access.py), [`data/source/`](../data/source/) |
| GitHub + README | Met | [`README.md`](../README.md) |
| Live demo | **Ready** | EC2 `i-0c53b195878f0ea5f` — http://ec2-3-235-22-143.compute-1.amazonaws.com:8080/ |
| Presentation | Out of repo | Use [`docs/demo_script.md`](demo_script.md) |

## Problem Inventory (Resolved / Tracked)

| ID | Severity | Issue | Resolution |
|----|----------|-------|------------|
| P1 | High | String compare `priority > "P2"` in incident analysis | Fixed: rank-based `_raise_priority()` |
| P2 | High | Legacy `iiq-*` names in agent instructions / deploy script | Fixed: `piter-*` naming in infra + `aws_deploy_fix.ps1` |
| P3 | High | `.env.example` drift (unused vars) | Fixed: aligned with [`app/config.py`](../app/config.py) |
| P4 | High | No running EC2 for teacher demo | **Resolved:** instance `i-0c53b195878f0ea5f`, validation in [`screenshots/deployment_validation.md`](../screenshots/deployment_validation.md) |
| P5 | Medium | `/api/chat` history ignored `session_id` | Fixed: `append_turn(session_id=...)` |
| P6 | Medium | Frontend `business_impact` vs `business_explanation` | Fixed: normalization exposes both |
| P7 | Medium | Bedrock errors looked like silent success | Fixed: `ok=false`, `error`, `fallback_used` on failures |
| P8 | Medium | Duplicate demo data files | Archived under `data/archive/` |
| P9 | Low | Missing `verify_credentials.py` / `verify_live_demo.py` | Added under `scripts/` |
| P10 | Low | Stale `iiq-*` in troubleshooting | Updated in docs pass |

## Final Knowledge Base Structure

```text
knowledge_base/
  runbooks/          (5 markdown runbooks)
  incidents/         (3 historical / similar-incident docs)
  services/          (3 service context docs)
  escalation/        (1 escalation policy)
  business_impact/   (1 impact matrix)
  piter/             (1 PITER workflow guide)
```

**S3 sync prefix:** `s3://<bucket>/projects/piter-aiops/knowledge_base/`

## Files Removed or Archived

| Path | Action | Reason |
|------|--------|--------|
| `data/demo_questions.json` | Archived | Duplicate of `evaluation/demo_questions.json` |
| `data/sample_alerts.json` | Archived | Validation-only; not used at runtime |
| `data/tool_test_cases.json` | Archived | Superseded by `evaluation/tool_evaluation_cases.json` |
| `data/escalation_rules.json` | Archived | Runtime uses `data/source/escalation_policies.json` |

Top-level `deployments.csv`, `historical_incidents.csv`, and `services.json` remain as **legacy fallbacks** for offline enrichment when `data/source/` is unavailable in trimmed Lambda zips; canonical runtime data is `data/source/`.

## AWS Architecture Checklist

See [`docs/ec2_deployment.md`](ec2_deployment.md) for the full checklist and CLI commands.

## Test Status

- **Offline:** `py -3.12 -m pytest -q` — **279 passed** (mocked Bedrock)
- **Live AWS:** `verify_credentials.py` OK, `agent_smoke_test.py` 6/6, `verify_live_demo.py` OK on EC2

## Demo Entry Points

- Local: `http://localhost:8080/` (Docker or `scripts/run-local.ps1`)
- **EC2:** http://ec2-3-235-22-143.compute-1.amazonaws.com:8080/
