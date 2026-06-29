# data/archive/ — quarantined legacy datasets

These files were the project's **earlier** data model. They are kept for
reference but are **no longer read** by the application, the four enrichment
tools, or the data layer — everything now reads exclusively from
`data/source/`.

## Quarantined here

| File / dir | Was used for | Replaced by (in `data/source/`) |
| --- | --- | --- |
| `agent_data/deploys.csv` (7-col) | deploy correlation | `deploys.csv` (12-col) |
| `agent_data/impact_matrix.csv` | business impact | `business_impact.json` |
| `agent_data/service_catalog.json` | owner / on-call | `service_owners.csv` + `on_call_schedule.csv` |
| `deployments.csv` | alt deploy feed | `deploys.csv` |
| `historical_incidents.csv` | similar incidents | `past_incidents.csv` |
| `incident_history.csv` (was in `sample_documents/`) | similar incidents | `past_incidents.csv` |
| `services.json` | service metadata | `service_owners.csv` |
| `external_status.json` | upstream status feed | (not part of the four canonical tools) |

## Why

`app/services/data_access.py` and `app/enrichment_tools.py` now resolve all
structured data from `data/source/` only, and the demo scenario was migrated
from the retired `postgres` example to the canonical `bet-service` P1 storm
trigger. Run `python scripts/validate_data.py` to confirm the canonical files
are present and no legacy runtime path has reappeared.

> Note: the per-Lambda data copies under `action_groups/*/data/` are deployment
> artifacts for the AWS Lambda runtime (a separate runtime from the Flask app)
> and are intentionally left in place.
