# EC2 Deploy — Frontend Rebuild (manual steps)

Document-only deploy plan. **Do not run SSH from CI.** Execute from your workstation when ready to ship after F4 passes.

## Prerequisites

- `frontend-redesign` merged to `main` locally.
- F4 gates green: `npm run build`, `pytest -q` (297+), manual click-test in `VERIFY.md`.
- AWS credentials and EC2 instance profile with Bedrock access (see `docs/ec2_deployment.md`).

## Numbered commands

1. **Merge branch locally** (on workstation):
   ```powershell
   git checkout main
   git merge frontend-redesign
   ```

2. **Pull latest and build Docker image** (workstation):
   ```powershell
   cd C:\dev\amdocs-ai-course\projects\piter-aiops
   git pull
   cd frontend
   npm run build
   cd ..
   docker build -t piter-aiops:latest .
   ```

3. **Transfer image to EC2** — choose one:
   - **Option A (recommended) — SSM + S3:** `.\scripts\deploy-ec2-ssm.ps1 -Verify` (no SSH). See [`docs/LOCAL_DEV.md`](../docs/LOCAL_DEV.md).
   - **Option B — rebuild on EC2:** `git pull` on the instance and `docker build` there (step 6).
   - **Option C — tarball + SSH:** `docker save` then `scp` and `docker load` on the instance.

4. **Confirm target instance** (workstation):
   ```powershell
   aws ec2 describe-instances --instance-ids ${PITER_EC2_INSTANCE_ID} `
     --query "Reservations[].Instances[].[InstanceId,State.Name,PublicDnsName]" --output table
   ```

5. **SSH to EC2** (replace key and host):
   ```bash
   ssh -i ~/.ssh/YOUR_KEY.pem ec2-user@${PITER_DEMO_HOST}
   ```

6. **On EC2 — update code/image** (if not using tarball):
   ```bash
   cd /opt/piter-aiops   # or your clone path
   git pull
   cd frontend && npm run build && cd ..
   docker build -t piter-aiops:latest .
   ```

7. **Stop and remove old container**:
   ```bash
   docker stop piter-aiops && docker rm piter-aiops
   ```

8. **Start new container**:
   ```bash
   docker run -d --name piter-aiops --restart unless-stopped -p 8080:8080 \
     --env-file /opt/piter-aiops/.env \
     -e PITER_USE_BEDROCK=true \
     piter-aiops:latest
   ```

9. **Local health on instance**:
   ```bash
   curl -s http://localhost:8080/api/health?deep=1
   ```

10. **Public health check**:
    ```bash
    curl -s http://localhost:8080/api/health?deep=1
    ```

11. **Browser smoke** — open `http://localhost:8080/` and run the checklist in `frontend/VERIFY.md`.

12. **Optional live demo script** (workstation):
    ```powershell
    python scripts/verify_live_demo.py --base-url http://localhost:8080
    ```

## Security notes

- Restrict security group port 8080 to demo audience; close after presentation.
- Never commit `.env` or secrets; use `/opt/piter-aiops/.env` on the instance only.

## Rollback

Redeploy the previous image tag or checkout a prior commit and rebuild. SPA bundles are **not** in version control — rebuild with `cd frontend && npm run build` from the target commit.
