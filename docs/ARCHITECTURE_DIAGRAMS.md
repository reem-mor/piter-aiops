# Architecture diagrams

Supplement to [`architecture.md`](architecture.md). These diagrams were extracted from the portfolio README for maintainability.

## High-level containers

```mermaid
flowchart LR
  subgraph client [Operator]
    SPA[React SPA]
  end
  subgraph app [PITER App — EC2 / Docker]
    Flask[Flask API]
    LocalRAG[Local TF-IDF fallback]
    Tools[Enrichment tools]
  end
  subgraph aws [AWS Bedrock — us-east-1]
    Agent[Bedrock Agent]
    KB[Knowledge Base]
    Lambdas[4 Action Group Lambdas]
    S3[(S3 KB corpus)]
  end
  SPA -->|REST| Flask
  Flask -->|invoke_agent| Agent
  Flask -.->|offline| LocalRAG
  Agent -->|retrieve + cite| KB
  Agent -->|enrich| Lambdas
  KB --- S3
  Lambdas --> Tools
```

## Triage sequence

```mermaid
sequenceDiagram
  autonumber
  participant Op as Operator
  participant UI as React SPA
  participant API as Flask API
  participant BR as Bedrock Agent
  participant KB as Knowledge Base
  participant AG as Action Groups

  Op->>UI: Alert storm / chat / triage
  UI->>API: POST /api/triage or /api/chat
  API->>API: Validate input + guardrails
  alt PITER_USE_BEDROCK=true
    API->>BR: invoke_agent
    BR->>KB: Retrieve runbooks
    BR->>AG: Enrichment tools
    BR-->>API: Answer + citations + trace
  else Fallback
    API->>API: Local TF-IDF over knowledge_base/
  end
  API-->>UI: priority, triage, sources, memory
```

## Action groups

```mermaid
flowchart LR
  Agent[Bedrock Agent] --> D & C & S & E
  D[piter-recent-deployments] --> D1[(deploys.csv)]
  C[piter-service-context] --> C1[(service_owners.csv)]
  S[piter-similar-incidents] --> S1[(past_incidents.csv)]
  E[piter-escalation] --> E1[(escalation_policies.json)]
  E -.->|preview only| SNS[SNS / SES]
```

| Action group | Data | Purpose |
|--------------|------|---------|
| `piter-recent-deployments` | `deploys.csv` | Correlate alert with recent deploys |
| `piter-service-context` | owners + impact | On-call and business context |
| `piter-similar-incidents` | `past_incidents.csv` | Historical match + MTTR |
| `piter-escalation` | policies | Escalation preview (no auto-send) |
