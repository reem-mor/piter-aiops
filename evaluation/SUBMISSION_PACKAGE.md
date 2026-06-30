# Phase 6 — Submission package

## Decisions (Phase 0)

See [`docs/PHASE0_DECISIONS.md`](../docs/PHASE0_DECISIONS.md).

## Screenshots

| File | Topic |
|------|-------|
| `screenshots/final/01_dashboard.png` | NOC dashboard |
| `screenshots/final/02_alert_storm.png` | Alert storm demo |
| `screenshots/final/03_triage_card.png` | Triage output |
| `screenshots/final/04_chat.png` | Chat / RAG |
| `screenshots/final/05_memory.png` | Session memory |
| `screenshots/final/06_kb.png` | Knowledge base |
| `screenshots/final/07_tools.png` | Tool enrichment |
| `screenshots/final/08_architecture.png` | Architecture |
| `screenshots/final/09_escalation_preview.png` | Escalation preview |

Presentation folder: [`presentation/README.md`](../presentation/README.md)

## Verification

```powershell
cd projects/piter-aiops
.\.venv\Scripts\python.exe -m pytest -q
docker compose up --build
```

## AWS (read-only inventory)

| Resource | ID |
|----------|-----|
| Bedrock Agent | `${PITER_BEDROCK_AGENT_ID}` (alias `live` / `${PITER_BEDROCK_AGENT_ALIAS_ID}`) |
| Knowledge Base | `${PITER_BEDROCK_KB_ID}` |
| S3 artifacts | `your-artifacts-bucket` |

KB sync commands (mutations require `APPROVED`): [`infra/KB_SYNC_COMMANDS.md`](../infra/KB_SYNC_COMMANDS.md)

## Acceptance

[`evaluation/ACCEPTANCE_CHECKLIST.md`](ACCEPTANCE_CHECKLIST.md)
