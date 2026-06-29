---
doc_id: "auth_service_login_failure"
title: "Auth Service Login Failure Runbook"
doc_type: "runbook"
services: "auth-service, redis-token-store, customer-db"
environments: "production, GIB-UKGC, NJ-DGE"
severity_applicable: "P1,P2,P3"
tags: "auth, login, deployment, tokens, session, outage"
last_updated: "2026-06-08"
author: "PITER AiOps"
version: "1.0"
---

# Auth Service Login Failure Runbook

Use this runbook when users cannot log in, token validation fails, MFA loops, or auth-service error rate increases after a production deployment.

## Investigation Steps

1. Confirm the production error rate, affected markets, and whether login failures started within 60 minutes of a deployment.
2. Check recent auth-service deployments, feature flags, schema migrations, and token-signing key changes.
3. Validate auth-service pod health, readiness probes, and `/health/ready` responses.
4. Check Redis token store latency, evictions, memory pressure, and primary/replica status.
5. Check customer-db connectivity for connection pool exhaustion, lock waits, and migration locks.
6. Confirm OIDC discovery and public API Gateway routes are returning valid responses.

## Triage Decision Tree

- If the latest deployment is within the last hour and failures started immediately after it, prepare rollback first.
- If login returns 401 for valid users and Redis has evictions or high latency, follow the Redis token store runbook.
- If auth-service pods are healthy but API Gateway returns 5xx, follow the API Gateway 5xx runbook.
- If customer-db has lock waits or exhausted connections, follow the database connectivity runbook.

## Remediation

1. Freeze additional auth-service releases until the incident commander approves.
2. Roll back the latest auth-service deployment if deployment correlation is strong and rollback is available.
3. Disable newly released feature flags for token validation, MFA routing, or session write behavior.
4. Restart only unhealthy auth-service pods after capturing logs.
5. Validate successful login rate and token issuance before declaring mitigation.

## Verification

- `auth_login_success_rate` returns to baseline.
- `auth_login_error_rate` stays below 1% for 10 minutes.
- Redis token writes and reads are stable.
- Synthetic login tests pass in production.

## Escalation

Escalate P1/P2 login incidents to Identity and Access primary on-call, then secondary on-call if no acknowledgement within the policy window. Produce a safe escalation preview only; do not send real escalation messages automatically.