# RAG Parity Results (Bedrock Agent vs Local KB)

- **Run at:** 2026-06-09 19:34:26 UTC
- **Agent ref:** `HH4YGSLZUE/O2EM03R4R3`
- **Score:** 1/6 semantic PASS

Parity criteria: same `grounded` decision, `expected_source_contains` on both sides, `answer_keywords` on both sides. Answer text may differ.

| ID | Status | Agent grounded | Local grounded | Root cause |
|----|--------|----------------|----------------|------------|
| 1 | FAIL | True | True | retrieval_mismatch |
| 2 | FAIL | True | True | retrieval_mismatch |
| 3 | FAIL | True | True | retrieval_mismatch |
| 4 | FAIL | True | True | eval_keywords_strict |
| 5 | FAIL | True | True | eval_keywords_strict |
| 6 | PASS | validation | validation | ok |

## Question 1

**Q:** What should I check when users cannot log in after the latest deployment?
**Status:** FAIL
**Parity failures:**
- expected source fragments not found on both sides

### Agent
- Grounded: True
- Matched: auth_service_login_failure.md
- Citations: ['auth_service_login_failure.md', 'auth_service_login_failure.md', 'historical_auth_incidents.md', 'auth_service.md', 'deployment_rollback.md']
- Preview: **Priority:**
Classify as P1 if many users across production cannot log in and revenue or customer access is affected. Classify as P2 if a subset of users or single region is impacted with workaround ...

### Local
- Grounded: True
- Matched: auth_service_login_failure.json
- Citations: ['auth_service_login_failure.json', 'historical_auth_incidents.json']
- Retrieval top: ['auth_service_login_failure.json', 'historical_auth_incidents.json']
- Side failures: ["citations missing sources: ['deployment_rollback']"]
- Preview: Priority:
Treat as P1/P2 until scope is confirmed because auth-service login failure can block all authenticated customer journeys.

Investigation findings:
The question matches the auth-service login...

## Question 2

**Q:** Analyze this alert: high error rate on auth-service in production after deployment.
**Status:** FAIL
**Parity failures:**
- expected source fragments not found on both sides

### Agent
- Grounded: True
- Matched: auth_service_login_failure.md
- Citations: ['auth_service_login_failure.md', 'historical_auth_incidents.md', 'auth_service_login_failure.md', 'deployment_rollback.md', 'historical_deployment_incidents.md']
- Side failures: ["citations missing sources: ['piter_workflow']", 'missing PITER sections (found: [])']
- Preview: **Priority:** P1  
High error rate on auth-service in production impacts ~50,000 users, with a business impact of $840,000/hour. SLA risk is critical, and regulatory exposure includes UKGC and DGE.

*...

### Local
- Grounded: True
- Matched: auth_service_login_failure.json
- Citations: ['auth_service_login_failure.json', 'auth_service_login_failure.json', 'deployment_rollback.json', 'auth_service_login_failure.json', 'auth_service_login_failure.json']
- Retrieval top: ['auth_service_login_failure.json', 'auth_service_login_failure.json', 'deployment_rollback.json', 'auth_service_login_failure.json', 'auth_service_login_failure.json']
- Side failures: ["citations missing sources: ['piter_workflow']", 'missing PITER sections (found: [])']
- Preview: Priority:
Treat as P1/P2 until scope is confirmed because auth-service login failure can block all authenticated customer journeys.

Investigation findings:
The question matches the auth-service login...

## Question 3

**Q:** Who should I escalate this incident to?
**Status:** FAIL
**Parity failures:**
- expected source fragments not found on both sides
- answer_keywords not satisfied on both sides

### Agent
- Grounded: True
- Matched: service_tier_impact.md
- Citations: ['service_tier_impact.md', 'escalation_policies_guide.md']
- Side failures: ["citations missing sources: ['auth_service']", "answer missing keywords: ['primary', 'safe preview']"]
- Preview: I cannot determine the correct escalation target without more information about your incident. To recommend who to escalate to, I need:

1. **Incident priority** — Is this P1, P2, P3, or P4?
2. **Affe...

### Local
- Grounded: True
- Matched: redis_token_store_degradation.json
- Citations: ['redis_token_store_degradation.json']
- Retrieval top: ['redis_token_store_degradation.json']
- Side failures: ["citations missing sources: ['escalation_policies', 'auth_service']", "answer missing keywords: ['primary', 'on-call', 'safe preview']"]
- Preview: Summary:
Escalation

Why this answer:
Grounded in redis_token_store_degradation.json (local knowledge base)....

## Question 4

**Q:** Are there similar incidents from the past?
**Status:** FAIL
**Parity failures:**
- answer_keywords not satisfied on both sides

### Agent
- Grounded: True
- Matched: similar_incidents_examples.md
- Citations: ['similar_incidents_examples.md', 'historical_deployment_incidents.md', 'historical_auth_incidents.md']
- Side failures: ["answer missing keywords: ['Redis']"]
- Preview: To answer your question about similar past incidents, I need you to provide details about the current incident you're investigating. Specifically, I need to know:

- Which service is affected?
- What ...

### Local
- Grounded: True
- Matched: similar_incidents_examples.json
- Citations: ['similar_incidents_examples.json', 'historical_auth_incidents.json', 'historical_deployment_incidents.json']
- Retrieval top: ['similar_incidents_examples.json', 'similar_incidents_examples.json', 'historical_auth_incidents.json', 'historical_auth_incidents.json', 'historical_deployment_incidents.json']
- Side failures: ["answer missing keywords: ['historical', 'auth-service', 'Redis']"]
- Preview: Summary:
Similar Incident Examples

Why this answer:
Grounded in similar_incidents_examples.json (local knowledge base)....

## Question 5

**Q:** What is the business impact of auth-service login failures in GIB-UKGC production?
**Status:** FAIL
**Parity failures:**
- answer_keywords not satisfied on both sides

### Agent
- Grounded: True
- Matched: auth_service_login_failure.md
- Citations: ['auth_service_login_failure.md', 'historical_auth_incidents.md', 'auth_service_login_failure.md', 'customer_revenue_sla_impact.md', 'business_impact_guide.md']
- Side failures: ["answer missing keywords: ['tier-0']"]
- Preview: **Business Impact: auth-service Login Failures (GIB-UKGC Production)**

**Priority:** P2

**Customer Impact:**
- Approximately 50,000 active users affected
- Customers cannot access accounts or comple...

### Local
- Grounded: True
- Matched: business_impact_guide.json
- Citations: ['business_impact_guide.json', 'auth_service_login_failure.json', 'auth_service_login_failure.json', 'auth_service_login_failure.json', 'business_impact_guide.json']
- Retrieval top: ['business_impact_guide.json', 'auth_service_login_failure.json', 'auth_service_login_failure.json', 'auth_service_login_failure.json', 'business_impact_guide.json']
- Side failures: ["answer missing keywords: ['tier-0']"]
- Preview: Priority:
Treat as P1/P2 until scope is confirmed because auth-service login failure can block all authenticated customer journeys.

Investigation findings:
The question matches the auth-service login...

## Question 6

**Q:** x
**Status:** PASS
- Agent validation: OK
- Local validation: OK
