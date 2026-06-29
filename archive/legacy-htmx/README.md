# Legacy HTMX console (archived)

Flask/Jinja HTMX workflow UI and `/ask` partials were retired in favor of the React SPA (`frontend/` → `app/static/spa/`).

## Contents

- `templates/` — former `app/templates/` (index, console partials, workflow result)
- `workflow.py`, `workflow_impact.py` — HTMX workflow payload builders
- `data/workflow_alerts.json` — static demo alerts for the old MVP workflow panel

## Active replacements

| Legacy | Current |
|--------|---------|
| `POST /workflow/triage` | `POST /api/triage` + storm P1 modal |
| `POST /ask` | `POST /api/chat` / `POST /api/follow-up` |
| HTMX bootstrap `workflow_alerts` | `GET /api/alert-stream` + `GET /api/bootstrap` |

Do not wire these paths back into `app/routes.py` without an explicit migration plan.
