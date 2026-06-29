---
doc_id: "redis_token_store_degradation"
title: "Redis Token Store Degradation Runbook"
doc_type: "runbook"
services: "redis-token-store, auth-service"
environments: "production, GIB-UKGC, NJ-DGE"
severity_applicable: "P1,P2,P3"
tags: "redis, session, token, auth, cache"
last_updated: "2026-06-08"
author: "PITER AiOps"
version: "1.0"
---

# Redis Token Store Degradation Runbook

Use this runbook when login succeeds intermittently, sessions disappear, token validation times out, or Redis latency/evictions rise.

## Investigation Steps

1. Check Redis `PING`, primary role, replica health, memory usage, and eviction count.
2. Compare Redis latency with auth-service token validation errors.
3. Check whether a recent auth-service deployment changed token write volume or TTL.
4. Inspect network errors between auth-service pods and Redis.
5. Confirm whether failover is active, partial, or stuck.

## Triage Decision Tree

- If Redis memory is above 90% and evictions are increasing, reduce token write pressure and scale memory.
- If primary is unavailable, follow the managed Redis failover process.
- If only auth-service sees errors, inspect client pool size and connection reuse.

## Remediation

1. Disable noisy token refresh paths or reduce refresh frequency if introduced by deployment.
2. Scale Redis memory or shard capacity if safe and pre-approved.
3. Restart auth-service clients only after confirming Redis itself is healthy.
4. Avoid `FLUSHDB` in production unless the incident commander and Identity owner approve.

## Verification

- Redis latency returns to normal.
- Evictions stop increasing.
- Login success and token validation rates recover.

## Escalation

Escalate to Identity and Access for auth impact and Data Platform if Redis failover or capacity changes are required.