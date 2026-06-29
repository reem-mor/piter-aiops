---
doc_id: "similar_incidents_examples"
title: "Similar Incident Examples"
doc_type: "incident"
services: "auth-service, api-gateway, redis-token-store, customer-db"
environments: "production"
severity_applicable: "P1,P2,P3"
tags: "similar incidents, examples, triage"
last_updated: "2026-06-08"
author: "PITER AiOps"
version: "1.0"
---

# Similar Incident Examples

## Login Failure Similarity Signals

- Same service: auth-service.
- Same timing: failure starts after production deployment.
- Same symptoms: login error rate, token validation failure, session loss, 401 for valid users.
- Same dependencies: Redis token store, customer-db, API Gateway.

## Gateway 5xx Similarity Signals

- Same public route or stage.
- Gateway 5xx mirrors backend 5xx.
- Recent route, WAF, certificate, or integration timeout change.

## Database Similarity Signals

- CPU high, lock waits, connection pool saturation, migration locks, replica lag.
- New query pattern after deployment.