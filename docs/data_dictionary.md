# Data Dictionary

## Canonical runtime data — `data/source/`

Used by incident analysis, alert storm, enrichment tools, and Lambda action groups:

- `alert_stream.csv`, `alerts.csv` — demo alert stream
- `deploys.csv` — deployment correlation
- `service_owners.csv` — ownership and on-call roles
- `past_incidents.csv` — similar incident lookup
- `business_impact.json`, `priority_matrix.json`, `escalation_policies.json` — scoring and escalation

Regenerate with `python scripts/generate_demo_data.py`.

## Legacy fallback — `data/agent_data/`

Used when `data/source/service_owners.csv` is unavailable (trimmed Lambda zip or old paths). Prefer `data/source/` for all new work.

## Top-level compatibility files

- `data/deployments.csv`, `data/historical_incidents.csv`, `data/services.json` — legacy fallbacks for enrichment when source catalog is missing
- `data/external_status.json` — external status demo data

## Archived validation files — `data/archive/`

Moved duplicates and unused JSON; see [`data/archive/README.md`](../data/archive/README.md).

## Demo / evaluation

- `evaluation/demo_questions.json` — presenter questions (canonical)
- `evaluation/tool_evaluation_cases.json` — tool contract expectations

## Knowledge base

- `knowledge_base/` — authoritative RAG corpus (14 markdown files)

## Validation

```powershell
python scripts/validate_data.py
python -m pytest tests/test_source_data.py tests/test_knowledge_base.py -q
```
