# Cleanup log

## 2026-06-09 — PITER readiness pass

- Archived duplicate JSON under `data/archive/` (`demo_questions.json`, `sample_alerts.json`, `tool_test_cases.json`, `escalation_rules.json`).
- Canonical demo questions: `evaluation/demo_questions.json`.
- Canonical KB S3 prefix: `projects/piter-aiops/knowledge_base/`.
- Renamed Bedrock action group references from legacy `iiq-*` to `piter-*` in agent instructions and `aws_deploy_fix.ps1`.
- Previous EC2 demo instance `i-03d3c5a59e849e5cf` was terminated 2026-05-31; relaunch documented in `docs/ec2_deployment.md`.

## 2026-05-31 — Post-demo teardown

- EC2 instance `i-03d3c5a59e849e5cf` terminated after screenshot capture.
- Validation recorded in `screenshots/deployment_validation.md`.
