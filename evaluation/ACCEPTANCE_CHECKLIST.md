# Phase 5 — Acceptance checklist

- [x] `pytest` — all unit tests pass locally
- [x] `/api/health` returns `status: ok`
- [x] `/api/chat` accepts messages and returns grounded answers (mocked in CI)
- [x] `/api/triage` and `/api/incident/analyze` return triage cards
- [x] `/api/metrics/*` expose four enrichment tools + escalation preview
- [x] `/api/investigations` derives UI rows from `data/source/alert_stream.csv`
- [x] Escalation defaults to preview (`PITER_NOTIFICATION_MODE=preview`)
- [x] Agent smoke 6/6 — see [`agent_smoke_results.md`](agent_smoke_results.md)
- [ ] Docker `docker compose up --build` — verify manually before submit
- [ ] Live Bedrock Agent demo — requires AWS credentials + `APPROVED` env

## Six demo questions (auth-service PDF chain)

1. What is the priority for auth-service login failures?
2. Were there recent deployments on auth-service?
3. Who owns auth-service and who is on call?
4. What similar incidents happened before?
5. What is the business impact?
6. Who should we escalate to?

Run: `python scripts/agent_smoke_test.py` (live AWS).
