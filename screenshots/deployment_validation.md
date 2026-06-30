# Deployment validation — 2026-06-09

Automated checks after PITER readiness pass, KB alignment, and EC2 relaunch.

## Local (Python 3.12)

| Check | Result |
|-------|--------|
| `py -3.12 -m pytest -q` | **279 passed** |
| `frontend npm ci && npm run build && npm run lint` | build OK; lint warnings only |
| `docker build -t piter-aiops:latest .` | OK |

## Bedrock KB

| Item | Value |
|------|--------|
| Knowledge base ID | `${PITER_BEDROCK_KB_ID}` |
| Data source ID | `${PITER_BEDROCK_DATA_SOURCE_ID}` |
| S3 prefix | `s3://your-artifacts-bucket/projects/piter-aiops/knowledge_base/` |
| Last ingestion | `(ingestion-job-id)` — 14 documents scanned, 0 failed |
| KB retrieve smoke | PASS (auth login runbook hits) |

## Bedrock Agent

| Item | Value |
|------|--------|
| Agent ID | `${PITER_BEDROCK_AGENT_ID}` |
| Alias ID | `${PITER_BEDROCK_AGENT_ALIAS_ID}` |
| Alias status | PREPARED (version 13) |
| `scripts/agent_smoke_test.py` | 6/6 PASS |
| `scripts/verify_credentials.py` | OK |

## Action groups

| Group | Lambda | Notes |
|-------|--------|-------|
| `piter-recent-deployments` | deployed | create/update in console if group missing |
| `piter-service-context` | deployed | create/update in console if group missing |
| `piter-similar-incidents` | deployed | create/update in console if group missing |
| `piter-escalation` | deployed | repointed via `aws_deploy_fix.ps1` |

Deploy script skips groups that do not yet exist on the agent draft; run `.\scripts\aws_deploy_fix.ps1` again after creating missing groups in the Bedrock console.

## Public EC2 (live demo)

| Item | Value |
|------|--------|
| Instance | `${PITER_EC2_INSTANCE_ID}` (`piter-aiops-demo`) — **running** |
| Public URL | http://localhost:8080/ |
| SPA routes | `/#live-kb`, `/#mvp` |
| `/health` | HTTP 200 `{"status":"ok"}` |
| `verify_live_demo.py` | PASS (Bedrock agent chat grounded) |

Validation:

```powershell
py -3.12 scripts/verify_live_demo.py --base-url http://localhost:8080
Invoke-RestMethod http://localhost:8080/api/health?deep=1
```

## Docker image artifact

Image tarball for EC2 bootstrap (not committed):

`s3://your-artifacts-bucket/projects/piter-aiops/deploy/piter-aiops.tar`

## Cleanup

See [`docs/cleanup_log.md`](../docs/cleanup_log.md). Terminate `${PITER_EC2_INSTANCE_ID}` after the presentation to avoid ongoing cost.
