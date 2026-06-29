---
doc_id: "payment_service"
title: "Payment Service Context"
doc_type: "service"
services: "payment-service, payments-service"
environments: "production, GIB-UKGC, NJ-DGE"
severity_applicable: "P1,P2,P3"
tags: "service ownership, payments, provider"
last_updated: "2026-06-08"
author: "PITER AiOps"
version: "1.0"
---

# Payment Service Context

Payment-service owns authorization, provider routing, deposit success, withdrawal processing, and payment-provider failover.

## Owner

- Team: Payments
- Primary escalation: Primary Payments On-Call
- Secondary escalation: Secondary Payments On-Call
- Channel: `#payments`

## Dependencies

- External payment gateway.
- Wallet service.
- API Gateway.

## Business Impact

Payment incidents can cause direct revenue loss, customer trust damage, and PCI-DSS/compliance follow-up.