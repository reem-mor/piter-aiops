---
doc_id: "database_connectivity"
title: "Database Connectivity Runbook"
doc_type: "runbook"
services: "customer-db, postgres, auth-service, payment-service"
environments: "production, GIB-UKGC, NJ-DGE"
severity_applicable: "P1,P2,P3"
tags: "database, postgres, connectivity, cpu, pool, locks"
last_updated: "2026-06-08"
author: "PITER AiOps"
version: "1.0"
---

# Database Connectivity Runbook

Use this runbook for PostgreSQL CPU saturation, connection pool exhaustion, lock waits, replica lag, or auth-service customer-db errors.

## Investigation Steps

1. Check database CPU, active connections, connection pool saturation, lock waits, and slow queries.
2. Compare database symptoms with the affected service deployment timeline.
3. Identify whether failures are reads, writes, or authentication-specific lookups.
4. Check replica lag before shifting read traffic.
5. Inspect the top queries and recent migrations for missing indexes or long transactions.

## Triage Decision Tree

- If CPU is high with one dominant query, mitigate the query or roll back the service that introduced it.
- If connections are exhausted, reduce client pool pressure before killing database sessions.
- If a migration lock is blocking auth-service reads or writes, involve DBA and service owner immediately.
- If replica lag affects reads only, remove the lagging replica from rotation.

## Remediation

1. Stop the newest deployment or feature flag that created the load.
2. Reduce service replica count or connection pool size if the database is overloaded by clients.
3. Kill only confirmed blocking sessions with DBA approval.
4. Roll back a schema or application change only when the rollback plan is verified.

## Verification

- CPU remains below alert threshold for 10 minutes.
- Connection pool saturation clears.
- Auth-service login checks pass.
- No new lock waits accumulate.

## Escalation

Escalate to Platform DBA for P1/P2 database incidents. Include service, query evidence, deployment correlation, business impact, and rollback status.