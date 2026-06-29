# Deployment

Consolidated deploy guide for local Docker and EC2. Detailed EC2 steps also live in [`ec2_deployment.md`](ec2_deployment.md) and [`LOCAL_DEV.md`](LOCAL_DEV.md).

## Prerequisites

- Python 3.12+, Node 20+ (build SPA only)
- Docker (local or EC2)
- AWS credentials when using live Bedrock (`aws sts get-caller-identity`)

## Local (2-hour quick path)

```powershell
cd projects/piter-aiops
py -3.12 -m pip install -r requirements-dev.txt
py -3.12 -m pytest -q
cd frontend; npm ci; npm run build; cd ..
docker compose up --build -d
```

Smoke:

```powershell
Invoke-RestMethod http://localhost:8080/api/health
Invoke-RestMethod http://localhost:8080/api/bootstrap
```

## Environment variables

Copy [`.env.example`](../.env.example). Key flags:

| Variable | Purpose |
|----------|---------|
| `PITER_LOCAL_FALLBACK` | Polished local KB when Bedrock fails |
| `PITER_DOCKER_USE_BEDROCK` | Enable Agent path in Docker |
| `BEDROCK_AGENT_ID` / `BEDROCK_AGENT_ALIAS_ID` | Live agent |
| `BEDROCK_KB_ID` | Knowledge Base |
| `PITER_ENABLE_LIVE_DISPATCH` | Real email/SMS (default off) |

## EC2 (SSM, no SSH)

```powershell
cd projects/piter-aiops
.\scripts\deploy-ec2-ssm.ps1 -Verify
```

On-instance script: [`scripts/ec2-deploy-from-s3.sh`](../scripts/ec2-deploy-from-s3.sh).

## Ship checklist

1. `npm run build` — commit `app/static/spa/` asset hash change
2. `pytest -q`
3. `py -3.12 scripts/verify_live_demo.py --base-url http://<host>:8080`
4. Hybrid fallback: set `PITER_LOCAL_FALLBACK=true` for class if AWS throttles

## Legacy note

HTMX console paths (`/ask`, `/workflow/triage`) are archived under [`archive/legacy-htmx/`](../archive/legacy-htmx/). Use the React SPA and `/api/*` endpoints only.
