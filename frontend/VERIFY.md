# PITER AiOps SPA — Verification (F2-R)

Manual click-test and automated gates for the enterprise layout + demo choreography.

## Automated gates

| Check | Command | Expected |
|-------|---------|----------|
| Production build | `cd frontend && npm run build` | `app/static/spa/index.html` + `assets/index-*.js` |
| ESLint | `cd frontend && npm run lint` | 0 errors |
| Playwright demo path | `cd frontend && npm run test:e2e` | Skips if server down; 4 specs when `:8080` is up |
| Backend tests | `pytest -q` (project root) | **297+** passed |
| Deep health | `curl http://localhost:8080/api/health?deep=1` | JSON `status` + `checks` |
| Live API smoke | `python scripts/verify_live_demo.py --base-url http://127.0.0.1:8080` | All checks OK |

## Serve locally

**Terminal 1 — backend:**

```powershell
cd projects\piter-aiops
.\scripts\run-local.ps1
```

Or: `.\.venv\Scripts\python.exe -m flask --app wsgi:app run -p 8080 --host=127.0.0.1`

**Terminal 2 — frontend hot reload (recommended for UI work):**

```powershell
cd frontend
npm run dev
```

| URL | Use |
|-----|-----|
| `http://localhost:5173/` | Daily UI iteration (Vite HMR; proxies `/api` to :8080) |
| `http://localhost:8080/` | Built SPA after `npm run build` |

After `npm run build`, **restart** the backend (Flask or `docker compose up --build -d`) so `:8080` serves the new asset hash. Docker Compose forces `FORCE_LEGACY_UI=false`; a developer `.env` with `FORCE_LEGACY_UI=true` disables the SPA on venv/Flask unless unset.

E2E expects `data-ui-version="demo-polish-v4"` on `.app-shell` — if tests skip with "Built demo-polish SPA not served", rebuild + restart.

See [`docs/LOCAL_DEV.md`](../docs/LOCAL_DEV.md).

## F2-R click-test matrix

- [ ] **Logo → Home** — Click PITER logo from every nav page; lands on Operations Dashboard.
- [ ] **Nav** — Operations, Analyzer, Agent Analytics, History, System & KB, Demo Guide (grouped sidebar).
- [ ] **Critical mode** — After P1 (~20s), shell gets red accent (`critical-mode` class); sticky P1 banner on dashboard.
- [ ] **Analyze P1 Incident** — Modal shows stepped progress; Home renders structured PITER cards (not raw markdown).
- [ ] **Safety guardrail** — Purple panel below analysis header; lists blocked auto-actions.
- [ ] **MTTR panel** — Demo-estimate KPIs after triage or storm complete.
- [ ] **Source badge** — Bedrock vs local fallback labeled correctly on analysis and chat.
- [ ] **Notify badge** — Top bar shows `NOTIFY LIVE` or `NOTIFY PREVIEW` matching `/api/bootstrap` `notification.mode` (may flash PREVIEW until bootstrap loads).
- [ ] **Start Alert Stream** — DEMO tag, alert table fills, KPIs tick, decisions feed updates.
- [ ] **P1 popup (~20s)** — Analyze / Escalate / Ask Agent / Continue Live; no overlapping modals.
- [ ] **Reset Demo** — Visible in demo mode; clears state for second run.
- [ ] **Alert row Ask agent** — Opens dock with context.
- [ ] **History toggles** — Alerts and Incidents views with search/filter.
- [ ] **System tools** — All four metrics forms; System/Metrics pages show live or preview banner per bootstrap.
- [ ] **Chat dock** — 420px width; no embedded full analysis; summary card + "View full analysis"; follow-up chips; New Session.
- [ ] **Escalation modal** — "Preview only — human approval required" banner; structured preview card; dispatch de-emphasized in preview mode.
- [ ] **Escalation dispatch** — See [Live vs preview](#live-vs-preview-escalation) below.

## Live vs preview escalation

| Mode | Local `.env` | Expected UI | Expected API |
|------|--------------|-------------|--------------|
| Preview | `PITER_NOTIFICATION_MODE=preview` | `NOTIFY PREVIEW`; mock/preview receipt on confirm | `sent: false` or `mode: mock` |
| Live | `PITER_NOTIFICATION_MODE=live`, `PITER_ENABLE_LIVE_DISPATCH=true`, allowlist + SES sender | `NOTIFY LIVE`; token field required | `mode: live`, `sent: true` (email) with valid token |

Live local test: set confirmation token in `.env` (`PITER_NOTIFICATION_CONFIRMATION_TOKEN=piter`), enter same token in escalation modal, use allowlisted recipient.

EC2 live demo: token and allowlist come from SSM Parameter Store under `/piter-aiops/notification/*` (see `scripts/sync-notification-params.ps1`).

## UI/UX extras (before EC2 ship)

- [ ] Forms: metrics inputs validate; chat empty message blocked.
- [ ] Escalation: error toast on missing token in live mode.
- [ ] Viewport ~1280px width — no clipped modals or sidebar overlap.
- [ ] After `npm run build`, hard refresh on `:8080` to pick up new asset hash.

## Screenshot checklist (8 shots)

1. Idle dashboard (no stream)
2. Alert stream with counter
3. P1 banner / modal
4. Analyze stepped progress
5. Structured PITER result + guardrail + MTTR
6. Slim chat dock with summary card
7. Escalation preview modal
8. History sections (sessions + context)

## Demo choreography (run twice)

1. Start Alert Stream → wait for P1 modal (~20s).
2. **Analyze P1 Incident** → structured panels on Home.
3. Open chat → follow-up chip → **View full analysis** scroll.
4. Escalation preview (no live send in preview mode).
5. Reset Demo between runs.

## Playwright

```powershell
cd projects\piter-aiops\frontend
npm run test:e2e
# optional: PITER_BASE_URL=http://ec2-host:8080 npm run test:e2e
```

## Docker (optional)

```powershell
docker compose up --build
curl http://localhost:8080/api/health?deep=1
```

## EC2 smoke (after deploy)

```powershell
.\scripts\deploy-ec2-ssm.ps1 -Verify
# or
python scripts/verify_live_demo.py --base-url http://ec2-3-235-22-143.compute-1.amazonaws.com:8080
```

Browser: `http://ec2-3-235-22-143.compute-1.amazonaws.com:8080/` — Ctrl+Shift+R, re-run click-test above.

Confirm SPA bundle: page source `index-*.js` should match `app/static/spa/index.html` from your local `npm run build`.

## Screenshots (presenter report)

Capture: Home idle, Home mid-storm, P1 popup, analysis view, escalation modal + receipt, Agent Analytics, History (both toggles), full-panel chat, NOTIFY LIVE badge.

## Rollback

Pre-rebuild SPA: commit `7e98a82` (`pre-frontend-rebuild snapshot`). On EC2: redeploy previous `piter-aiops.tar` from S3.
