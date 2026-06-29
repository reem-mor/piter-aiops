# Lambda Setup

Each Lambda should:

- Read structured data from packaged CSV/JSON files or a safe S3 object.
- Return structured JSON.
- Catch exceptions and return a safe error object.
- Never send escalation notifications directly.

Recommended functions:

- `piter-recent-deployments`
- `piter-service-context`
- `piter-similar-incidents`
- `piter-escalation-preview`

Test each function with the payloads in `data/tool_test_cases.json`.
