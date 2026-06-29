---
doc_id: "api_gateway"
title: "API Gateway Context"
doc_type: "service"
services: "api-gateway"
environments: "production, GIB-UKGC, NJ-DGE"
severity_applicable: "P1,P2,P3"
tags: "service ownership, gateway, ingress"
last_updated: "2026-06-08"
author: "PITER AiOps"
version: "1.0"
---

# API Gateway Context

API Gateway owns public routing, stage configuration, WAF attachment, TLS/domain mapping, throttling, and backend integrations.

## Owner

- Team: Edge Platform
- Primary escalation: Primary Edge Platform On-Call
- Secondary escalation: Secondary Edge Platform On-Call
- Channel: `#edge-platform`

## Dependencies

- Auth-service for authenticated routes.
- Backend service integrations.
- WAF, TLS certificate, and DNS.

## Business Impact

Gateway incidents can make healthy services unreachable. Always determine whether gateway errors mirror backend errors before escalating.