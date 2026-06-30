# Local Development — PITER AiOps

Develop on your Windows workstation with Cursor. Ship to EC2 only for live demos.

**EC2 instance:** `${PITER_EC2_INSTANCE_ID}` — http://localhost:8080/

## Mental model

```text
Local (daily)     →  Vite :5173 + Flask/Docker :8080
EC2 (demo ship)   →  build SPA → docker build → docker run on instance
```

Production on EC2 runs **Gunicorn inside Docker**, not `flask run --debug`. The SPA is copied into the image at build time ([`Dockerfile`](../Dockerfile)).

## Generic advice vs PITER

| Common suggestion | PITER reality |
|-------------------|---------------|
| `FLASK_DEBUG=1` on EC2 | Use local dev; keep EC2 production-like |
| rsync source to EC2 | Bypasses Docker and leaves stale SPA assets |
| `python app.py` on EC2 | Use `docker run` with Gunicorn ([`wsgi:app`](../wsgi.py)) |
| Port 5000 | App listens on **8080** only |
| Cursor Remote-SSH as editor | Optional for logs/ops; not the primary dev loop |
| `inotify` file watcher | Not needed on Windows; use local Vite HMR |

## Daily loop

### Backend (pick one)

**Option A — venv (fastest for Python changes)**

```powershell
cd C:\dev\amdocs-ai-course\projects\piter-aiops
.\scripts\run-local.ps1
```

Serves `http://127.0.0.1:8080` via [`app.py`](../app.py).

**Option B — Flask CLI (equivalent)**

```powershell
.\.venv\Scripts\python.exe -m flask --app wsgi:app run -p 8080 --host=127.0.0.1
```

Note: [`wsgi.py`](../wsgi.py) only exports `app` for Gunicorn — running `python wsgi.py` does not start a server.

**Option C — Docker (parity with EC2)**

```powershell
docker compose up --build
```

Offline by default. Live Bedrock in Docker: `$env:PITER_DOCKER_USE_BEDROCK = "true"` then rebuild. See [`docker-compose.yml`](../docker-compose.yml).

### Frontend (F2-R SPA)

With backend on 8080:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` and `/health` to 8080 ([`vite.config.ts`](../frontend/vite.config.ts)).

Edit `frontend/src/**` in Cursor; changes hot-reload through Vite. No EC2 involvement.

### Where to change what

| Goal | Primary files |
|------|----------------|
| Layout, nav, top bar | `frontend/src/components/shell/` (`AppShell`, `Sidebar`, `TopBar`) |
| Pages / screens | `frontend/src/pages/` (`Home`, `Metrics`, `SystemMetrics`, …) |
| Buttons, modals, demo flow | `frontend/src/components/demo/` (`P1Modal`, `EscalationModal`) |
| NOC cards, badges | `frontend/src/components/noc/` |
| Global look | `frontend/src/styles.css` |
| shadcn primitives | `frontend/src/components/ui/` |
| API client types | `frontend/src/lib/api-contract.ts`, `frontend/src/types/api.ts` |
| API response shape (server) | `app/routes.py`, `app/services/` |

If you change an API field, update **both** backend and `api.ts` plus the component that renders it.

### Pre-ship gates

| Check | Command |
|-------|---------|
| SPA build | `cd frontend && npm run build` |
| Tests | `pytest -q` (297+ expected) |
| Deep health | `Invoke-RestMethod http://localhost:8080/api/health?deep=1` |

Full click-test matrix: [`frontend/VERIFY.md`](../frontend/VERIFY.md).

## EC2 deploy (demo only)

Three steps: **build SPA → build image → restart container**. The SPA is baked into the image at `docker build` time ([`Dockerfile`](../Dockerfile)).

### Path A — SSH (`deploy-ec2.ps1`)

```powershell
.\scripts\deploy-ec2.ps1
.\scripts\deploy-ec2.ps1 -Execute -SshKey C:\path\to\key.pem
.\scripts\deploy-ec2.ps1 -Verify
```

Requires security group port **22** from your IP. Manual steps: [`frontend/EC2_DEPLOY.md`](../frontend/EC2_DEPLOY.md).

### Path B — SSM + S3 (recommended when SSH is blocked)

One-shot from project root:

```powershell
.\scripts\deploy-ec2-ssm.ps1 -Verify
```

Or step by step:

```powershell
docker build -t piter-aiops:latest .
docker save piter-aiops:latest -o piter-aiops.tar
aws s3 cp piter-aiops.tar s3://your-artifacts-bucket/projects/piter-aiops/deploy/piter-aiops.tar
aws s3 cp scripts/ec2-deploy-from-s3.sh s3://your-artifacts-bucket/projects/piter-aiops/deploy/ec2-deploy-from-s3.sh
aws ssm send-command --instance-ids ${PITER_EC2_INSTANCE_ID} `
  --document-name AWS-RunShellScript `
  --parameters file://scripts/ssm-deploy-image.json
```

[`scripts/ec2-deploy-from-s3.sh`](../scripts/ec2-deploy-from-s3.sh) loads the image, merges notification keys from SSM Parameter Store into `/opt/piter-aiops/.env`, and restarts the container. Bedrock/S3 settings on the instance are preserved.

### Path C — notification/env only (no new image)

```powershell
.\scripts\deploy-ec2-ssm.ps1 -NotificationOnly -Verify
```

Or: `aws ssm send-command` with [`scripts/ssm-patch-notification-live.json`](../scripts/ssm-patch-notification-live.json).

### Post-deploy verify

```powershell
python scripts/verify_live_demo.py --base-url http://localhost:8080
```

Browser: hard refresh (Ctrl+Shift+R), then [`frontend/VERIFY.md`](../frontend/VERIFY.md) click-test.

**Do not** rsync project trees to EC2 for routine development.

### Daily rhythm

1. `run-local.ps1` + `npm run dev` → iterate UI on `:5173`
2. `npm run build` + VERIFY.md on `:8080` before lunch
3. `deploy-ec2-ssm.ps1 -Verify` before demo
4. Rollback: redeploy previous `piter-aiops.tar` from S3 or prior git commit under `app/static/spa/`

## SSH (ops only)

Configure once in `~/.ssh/config`:

```sshconfig
Host piter-demo
  HostName ${PITER_DEMO_HOST}
  User ec2-user
  IdentityFile C:/path/to/YOUR_KEY.pem
```

Useful commands:

```bash
ssh piter-demo "docker logs -f --tail 100 piter-aiops"
ssh piter-demo "curl -s http://localhost:8080/api/health?deep=1"
ssh piter-demo "docker ps"
```

Security group: **22** from your IP; **8080** for demo audience only ([`ec2_deployment.md`](ec2_deployment.md)).

## Optional: Cursor Remote-SSH

Install Remote-SSH only if you need to inspect files or logs on the instance. Prefer local editing + `deploy-ec2.ps1` for code changes.

## Related docs

| Document | Purpose |
|----------|---------|
| [`frontend/VERIFY.md`](../frontend/VERIFY.md) | F2-R verification checklist |
| [`frontend/EC2_DEPLOY.md`](../frontend/EC2_DEPLOY.md) | Manual EC2 deploy steps |
| [`ec2_deployment.md`](ec2_deployment.md) | AWS resources and launch checklist |
| [`troubleshooting.md`](troubleshooting.md) | Common failures |
| [`environment.md`](environment.md) | `.env` variables |
