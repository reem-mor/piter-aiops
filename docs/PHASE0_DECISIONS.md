# Phase 0 — Resolved Decisions

Approved as part of the full implementation plan (2026-06-09). Use this document as the acceptance baseline when the PDF is unavailable.

## Requirements source

- **Primary:** [`README.md`](../README.md) + [`resources/handouts/mid-course-project-guidelines.docx`](../../resources/handouts/mid-course-project-guidelines.docx)
- **PDF** `PITER_AiOps_-_Mid-Course_Project_Instructions.pdf` was not found in the repo.

## Foundation model

- **Keep** live AWS model: `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (Agent `${PITER_BEDROCK_AGENT_ID}`, alias `live`).
- Do not switch to Nova Lite without an explicit AWS change request and instructor approval.

## Demo storyline

| Use case | Canonical data |
|----------|----------------|
| PDF chat Q1–6 (auth login failure) | `auth-service` in `data/source/` + KB runbooks |
| Alert storm / NOC console | `bet-service` P1 trigger in `data/source/alert_stream.csv` |
| Wallet `v4.12.3` chain | **Not** live — do not demo unless `scripts/generate_demo_data.py` is re-run with seed 42 |

## Folder structure

| PDF name | Repo path | Action |
|----------|-----------|--------|
| `backend/app/` | `app/` | Keep path; see [`STRUCTURE.md`](STRUCTURE.md) |
| `lambdas/` | `action_groups/` | Keep path |
| `presentation/` | `screenshots/final/` | `presentation/README.md` points here |

## Knowledge base format

- **AWS Bedrock KB:** Markdown on S3 (`projects/piter-aiops/knowledge_base/**/*.md`)
- **Local offline RAG:** JSON under `knowledge_base/**/*.json`
- Sync procedure: [`infra/KB_SYNC_COMMANDS.md`](../infra/KB_SYNC_COMMANDS.md) (AWS mutations require `APPROVED`)

## Production chat path

- Default: Bedrock Agent (`PITER_RAG_BACKEND=agent`, `PITER_USE_BEDROCK=true`)
- Local TF-IDF fallback only when `PITER_LOCAL_FALLBACK=true` or `USE_BEDROCK=false`
- Escalation: preview-only unless all live-dispatch gates are explicitly enabled
