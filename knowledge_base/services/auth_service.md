---
doc_id: "auth_service"
title: "Auth Service Context"
doc_type: "service"
services: "auth-service"
environments: "production, GIB-UKGC, NJ-DGE"
severity_applicable: "P1,P2,P3"
tags: "service ownership, auth, login"
last_updated: "2026-06-08"
author: "PITER AiOps"
version: "1.0"
---

# Auth Service Context

Auth-service owns login, session validation, token issuance, MFA handoff, and OIDC callbacks.

## Owner

- Team: Identity and Access
- Primary escalation: Primary Identity and Access On-Call
- Secondary escalation: Secondary Identity and Access On-Call
- Channel: `#identity-access`

## Dependencies

- Redis token store for session and token state.
- Customer database for user account lookup.
- API Gateway for public auth routes.

## Business Impact

Auth-service is tier-0. Login failure can block all revenue-generating flows because users cannot reach wallet, payments, or product actions.