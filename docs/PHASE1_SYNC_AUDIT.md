# Phase 1 — Sync Audit (Read-Only)

**Date:** 2026-06-10  
**Local git HEAD:** `7e17e70` — *Implement triage client enhancements and streamline triage question generation*

## Deployment drift

| Target | Status | Evidence |
|--------|--------|----------|
| **EC2 backend + SPA** | **In sync with local repo** | Served SPA assets match local build: `index-Cfs3WLaY.js`, `index-LqVZ4E_C.css`. `/api/health?deep=1` → all checks ok. `/api/bootstrap` → `kb_id: RBTJM6NIG9`, `rag_backend: agent`, `use_bedrock: true`. |
| **Lovable frontend** | **Drift — separate build** | https://ops-insight-nexus.lovable.app serves `index-3wpC2u22.js`, title *IncidentIQ*, Lovable badge. No Flask API (`/api/bootstrap` returns HTML). Cannot run Bedrock/memory/escalation flows standalone. |
| **Git vs EC2 code** | **No version endpoint** | Best-effort: SPA hash match + deep health + bootstrap config align with local HEAD. SSH not used (read-only). |

## AWS resources (profile `reemmor`, `us-east-1`)

| Resource | Status | Evidence |
|----------|--------|----------|
| Agent `HH4YGSLZUE` | PREPARED | `get-agent` — `incidentiq-triage-agent`, prepared 2026-06-09 |
| Alias `O2EM03R4R3` | PREPARED | Routes to agent version **21** |
| KB `RBTJM6NIG9` | ENABLED on agent DRAFT | `list-agent-knowledge-bases` |
| Action groups (×4) | ENABLED | `piter-recent-deployments`, `piter-service-context`, `piter-similar-incidents`, `piter-escalation` |
| Lambdas (×4) | Active, python3.12 | Last modified 2026-06-09 |

## Requirements checklist

| Requirement | Status | Evidence |
|-------------|--------|----------|
| KB attached to agent | **Met** | AWS: KB `RBTJM6NIG9` ENABLED on agent `HH4YGSLZUE` |
| boto3 `invoke_agent` | **Met** | `app/bedrock_agent_client.py:137` — `self._client.invoke_agent(**request)` |
| Session memory (follow-up context) | **Met** | `app/services/session_memory.py` — `append_followup()` L200–208; `app/routes.py` triage/follow-up |
| Chat history persistence | **Met** | `app/services/chat_history.py` — `append_turn()` L95–110; `GET/DELETE /api/history` in `app/routes.py` |
| Pandas / CSV / JSON | **Met** | `app/services/data_access.py` — `pd.read_csv` L109/141; loaders for `data/source/*.csv` and `*.json` |
| 4 metric / Lambda functions | **Met** | `action_groups/piter-*/lambda_function.py`; AWS Lambdas + action groups all ENABLED |
| Flask APIs | **Met** | `app/routes.py` — `/api/chat`, `/api/triage`, `/api/metrics/*`, `/api/history` |
| Docker | **Met** | `Dockerfile`, `docker-compose.yml` |
| EC2 deployment | **Met** | http://ec2-3-235-22-143.compute-1.amazonaws.com:8080/ — deep health ok |

## Screenshot capture note

Functional screenshots (Bedrock, memory, escalation, citations) require the **EC2 integrated stack** (same SPA as repo). Lovable URL is a standalone frontend fork without API backend.
