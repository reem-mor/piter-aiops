# F2-R Frozen API Contract (amended)

Frontend-only branch `frontend-redesign`. All UI data comes from these endpoints — no invented `/api/tools/status`, no frontend mock rows.

## Core (F1)

| Method | Path | Use |
|--------|------|-----|
| GET | `/api/health` | Liveness; `?deep=1` for infrastructure status (app, S3, Bedrock) |
| POST | `/api/chat` | Agent chat + follow-up when `session_id` set |
| POST | `/api/incident/analyze` | Manual analyzer pipeline |
| GET | `/api/history` | Chat messages for one session (`?session_id=`) |
| DELETE | `/api/history` | Clear session history |
| GET | `/api/investigations` | Incident queue cards (`?limit=`) |

## Demo / stream (F2-R amendment)

| Method | Path | Use |
|--------|------|-----|
| GET | `/api/bootstrap` | CSRF, KB/S3 ids, notification mode, `alert_stream` summary |
| GET | `/api/alert-stream` | Storm corpus; `?include_rows=true` for client playback |
| POST | `/api/triage` | P1 analyze from alert row (same enrichment as analyze) |
| POST | `/api/follow-up` | Contextual follow-up after triage session |
| POST | `/api/escalation/notify` | On-call dispatch (mock/preview gated; UI shows receipt) |
| GET | `/api/metrics/business-impact` | Demo-only KPI enrichment (MTTR/cost) after storm completes |
| GET | `/api/demo-alert` | Canned P1 payload (console; storm uses stream `p1_trigger`) |
| GET | `/api/sessions/:id/history` | Triage session detail (optional) |

## Metrics tools (System page)

| Method | Path |
|--------|------|
| GET | `/api/metrics/recent-deployments` |
| GET | `/api/metrics/service-context` |
| GET | `/api/metrics/similar-incidents` |
| GET | `/api/metrics/escalation-preview` |

## Client-side storm playback

No server SSE. UI loads `GET /api/alert-stream?include_rows=true` once, animates by `seconds_offset`:

- P1 modal at **20s** wall clock (`P1_WALL_SECONDS`)
- Full storm **90s** wall (`STORM_WALL_SECONDS`)
- Data P1 trigger at offset **175s** in CSV (300s corpus)

## Escalation mock verification

POST `/api/escalation/notify` with `confirmation_token` from bootstrap `csrf_token`. In default env (`PITER_NOTIFICATION_MODE=mock`), response has `sent: false` / `blocked: true` — no SNS/SES. Demo UI still marks incident **Escalated** and shows dispatch receipt toast.

## Chat sessions

`GET /api/history` returns one session per request. Dock maintains a client-side session list from triage/chat `session_id` values.

## Removed from UI (not in contract)

- `/api/tools/status` — use health deep instead
- `/api/kb/manifest` — KB shown as bootstrap config on System page only
