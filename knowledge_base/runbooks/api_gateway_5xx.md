---
doc_id: "api_gateway_5xx"
title: "API Gateway 5xx Troubleshooting Runbook"
doc_type: "runbook"
services: "api-gateway, auth-service, payment-service"
environments: "production, GIB-UKGC, NJ-DGE"
severity_applicable: "P1,P2,P3"
tags: "api-gateway, 5xx, ingress, routing, timeout"
last_updated: "2026-06-08"
author: "PITER AiOps"
version: "1.0"
---

# API Gateway 5xx Troubleshooting Runbook

Use this runbook when API Gateway returns 5xx, 502, 503, or 504 errors for production traffic.

## Investigation Steps

1. Identify failing route, stage, integration target, and market.
2. Compare API Gateway 5xx with backend service 5xx, latency, and health checks.
3. Check recent deployments to API Gateway routing, auth-service, and upstream services.
4. Inspect integration timeout, throttling, WAF blocks, and certificate errors.
5. Validate whether public synthetic checks fail from multiple regions.

## Triage Decision Tree

- If backend errors mirror gateway errors, follow the backend service runbook.
- If backend is healthy but gateway fails, inspect route configuration and integration timeout.
- If only authenticated routes fail, check auth-service and token validation.

## Remediation

1. Roll back recent gateway route or stage configuration changes.
2. Shift traffic away from a failing integration target if supported.
3. Increase backend capacity only after confirming saturation is the cause.
4. Avoid deleting stages or custom domain mappings during an incident.

## Verification

- Gateway 5xx drops below 1%.
- p99 latency returns to normal.
- Synthetic checks pass for authenticated and anonymous routes.

## Escalation

Escalate to Edge Platform for gateway configuration or WAF issues, and to the backend owner when integration errors mirror service errors.