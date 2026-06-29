# Knowledge base layout

## `knowledge_base/`

Indexed corpus for Bedrock KB and local TF-IDF fallback.

| Area | Contents |
|------|----------|
| `piter/` | PITER workflow policy, severity matrix, escalation rules |
| `runbooks/` | Service runbooks (auth, payments, API gateway, database) |
| `postmortems/` | Historical incident write-ups for similarity context |
| `policies/` | Regulatory and on-call policy snippets |

Metadata: `docs/kb/catalog.csv`.

## `data/source/`

Operational CSV/JSON used by Action Groups and the alert storm demo.

| File | Role |
|------|------|
| `alert_stream.csv` | 400-row storm; P1 trigger `ALT-2026-06-10-0251` at offset 175 (~20s playback) |
| `deployments.csv` | Recent deployment suspect tool |
| `incidents.csv` | Similar incidents tool |
| `escalation_matrix.json` | Escalation preview tool |
| `service_context.json` | Service ownership and dependencies |

## `data/archive/`

Quarantined legacy datasets — not loaded at runtime.

## `archive/legacy-htmx/data/`

Archived `workflow_alerts.json` for tests only; not exposed in `/api/bootstrap`.
