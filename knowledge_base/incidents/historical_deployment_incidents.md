---
doc_id: "historical_deployment_incidents"
title: "Historical Deployment Incidents"
doc_type: "incident"
services: "auth-service, bet-service, api-gateway"
environments: "production, GIB-UKGC, NJ-DGE"
severity_applicable: "P1,P2"
tags: "historical, deployment, rollback"
last_updated: "2026-06-08"
author: "PITER AiOps"
version: "1.0"
---

# Historical Deployment Incidents

## INC-DEPLOY-2026-06-10

Bet-service P1 in GIB-UKGC followed a retry-policy deployment. Root cause was retry fan-out causing connection pool saturation. Resolution was rollback, restart of saturated pods, and circuit breaker validation.

## INC-DEPLOY-2026-05-12

Auth-service P2 began minutes after a feature flag rollout. Root cause was token validation logic rejecting a subset of valid sessions. Resolution was feature flag disablement and then code rollback.

## Reuse Guidance

If the latest deployment is within one hour of the alert and rollback is available, prepare rollback while continuing dependency checks.