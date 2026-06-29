# AWS Bedrock setup

Hybrid mode: live Bedrock Agent + Knowledge Base when configured; labeled local fallback when not.

Full infra steps: [`infra/bedrock_agent_setup.md`](../infra/bedrock_agent_setup.md).

## Agent

- Name: `piter-aiops-incident-response-agent`
- Attach KB with S3 prefix `projects/piter-aiops/knowledge_base/`
- Action groups (Lambda): recent deployments, service context, similar incidents, escalation preview
- After changes: prepare draft → new version → update alias → set `BEDROCK_AGENT_ALIAS_ID` in `.env`

## Knowledge Base

- Corpus in repo: `knowledge_base/`
- Sync (non-destructive when corpus changed):

```powershell
py -3.12 scripts/sync_knowledge_base.py --ingest --wait
```

## Verify (read-only)

```powershell
aws sts get-caller-identity
py -3.12 scripts/verify_credentials.py
py -3.12 scripts/agent_smoke_test.py
```

## Hybrid fallback

Set `PITER_LOCAL_FALLBACK=true` (default in `.env.example`). The UI shows an offline KB banner when `fallback_used` is true. Local path uses TF-IDF over the same corpus — not generic placeholder text.

## IAM

Do not run destructive IAM scripts in class. `scripts/aws_deploy_fix.ps1` may reference legacy role names — prefer `piter-*` resources documented in [`ec2_deployment.md`](ec2_deployment.md).
