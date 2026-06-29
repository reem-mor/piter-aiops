# Demo script (14 steps)

## Setup

1. Open http://localhost:8080/ or EC2 URL from [`deployment.md`](deployment.md).
2. `GET /api/health` and `/api/bootstrap` return `ok`.
3. Optional: `GET /api/health?deep=1` for `bedrock_agent_configured`, `memory_writable`, `tools_ok`.

## Presenter flow (~5 minutes)

1. **Intro** — PITER = Priority, Investigation, Triage, Escalation, Resolution; grounded in KB + tools.
2. Click **Start Alert Stream** — storm timer and alert count appear in the top bar.
3. Watch alerts populate; noise suppression KPI updates.
4. At **~20s** — P1 modal fires; shell enters **critical mode** (red accent).
5. Click **Analyze P1 Incident** — stepped progress in modal; triage runs; Home shows **P1 analysis** with structured PITER cards.
6. Point to **Safety guardrail** (no auto rollback/failover) and **MTTR demo estimates**.
7. Point to **Priority** and **Business impact** field cards.
8. Point to **Investigation** — bullet lists, deployment suspect, similar incidents table.
9. Expand **Triage** timeline and **Escalation** owner/on-call fields.
10. Open **Agent Chat** (420px) — compact summary card, **View full analysis**, source badge.
11. Tap a **follow-up chip** or ask: `What should I check next?` — uses `/api/follow-up` (same session_id).
12. **New Session** or **Clear** in chat dock — fresh context.
13. **History** — Conversation history, incident context card, past investigations.
14. **Escalate On-Call** — "Preview only — human approval required" unless NOTIFY LIVE.
15. **Demo Guide** page in sidebar for 60–90s recap.
16. **Close** — Source badge: Bedrock Agent + KB vs local fallback (never mislabeled).

## Pre-class commands

```powershell
aws sts get-caller-identity
cd projects/piter-aiops
py -3.12 -m pytest -q
cd frontend; npm run build; cd ..
py -3.12 scripts/verify_credentials.py
py -3.12 scripts/agent_smoke_test.py
py -3.12 app.py
py -3.12 scripts/verify_live_demo.py --base-url http://<host>:8080
```

## Sample triage payload

```json
{
  "service": "bet-service",
  "environment": "GIB-UKGC",
  "severity": "P1",
  "symptom": "100% error rate on bet placement",
  "alert_time": "2026-06-10T10:02:00Z",
  "alert_id": "ALT-2026-06-10-0251"
}
```

POST `/api/triage`.
