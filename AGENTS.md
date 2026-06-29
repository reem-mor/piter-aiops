# AGENTS.md — PITER AiOps

Agentic **incident-response platform** — AWS Bedrock Agent, RAG, Flask, React, Docker, ~325 pytest tests.

## Conventions

- Python **3.12** · `pip install -r requirements-dev.txt`
- SPA: `cd frontend && npm ci && npm run build` → `app/static/spa/` (gitignored)
- **Never commit** `.env`, SPA bundles, or live AWS resource IDs in docs
- Run `pytest -q` before PRs; PITER has its own CI in `.github/workflows/ci.yml`

## Scope

Production-minded ops code — prefer observability, safe escalation, and grounded RAG over refactors.
