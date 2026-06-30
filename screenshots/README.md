# PITER AiOps Screenshots

Use `screenshots/final/` for the mid-project submission and live-demo README.
These captures match the current React dashboard, Flask API flow, PITER memory
screen, Knowledge Base view, tool results, and Docker/test proof.

## Final Submission Set

| File | Shows |
|------|-------|
| `final/01_dashboard.png` | Current React dashboard |
| `final/02_investigations_table.png` | Incident history / investigation queue |
| `final/03_alert_storm_running.png` | Alert storm running |
| `final/04_p1_detected.png` | P1 candidate detected |
| `final/05_investigation_detail_triage.png` | Structured PITER triage |
| `final/06_rag_citations.png` | Knowledge Base citations |
| `final/08_memory_followup_context.png` | Session memory follow-up |
| `final/09_escalation_preview.png` | Safe escalation preview (recipients masked) |
| `final/10_post_mortem_summary.png` | Resolution/post-mortem view |
| `final/11_knowledge_base.png` | Knowledge Base + upload runbook panel |
| `final/13b_settings_aws_status.png` | AWS / Bedrock status — agent config + 4 registered action groups |
| `final/14b_live_demo_checks.png` | Live demo verification proof (29/29 checks) |
| `final/15_docker_running.png` | Docker container proof |
| `final/16_structured_analysis_panel.png` | Structured analysis — correlation chain, no raw markdown |
| `final/demo-wallet-v4-12-3-correlation-chain.png` | Wallet-service v4.12.3 deploy → replication lag → similar incident |

> **Pruned (Jun 10, 2026):** `07_lambda_mcp_tools.png`, `12_upload_document_flow.png`, `13_architecture_settings.png` (older Lovable UI, superseded by current-UI captures), `14_tests_passing.png` (noisy terminal capture — see `14b`), `17_tokenless_escalation_modal.png` (unmasked recipient emails; `09` now masks PII).

## Regenerate (Jun 2026 submission set)

```powershell
cd C:\dev\amdocs-ai-course\projects\piter-aiops\frontend
npm ci
$env:PITER_BASE_URL = "http://localhost:8080"
npx playwright test e2e/submission-screenshots.spec.ts --project=chromium
```

Captures at **1920×1080** against the live EC2 stack (Bedrock + memory + escalation). The Lovable URL is a static frontend preview only — it has no Flask API backend.

## Legacy Captures

`archive/legacy-root/`, `console_demo/`, and `extras/` are historical captures
from earlier UI or AWS proof flows. Keep them for audit if useful, but do not
use them as the primary README or live-submission screenshots unless the
instructor specifically asks for those older proof filenames.

To capture against a local stack instead, set `$env:PITER_BASE_URL = "http://127.0.0.1:8080"` (requires `docker compose up --build -d` with the same built SPA version).
