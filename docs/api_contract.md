# API Contract

## `GET /api/tools/status`

Returns the four required enrichment tools and readiness status.

## `GET /api/history`

Returns process-local chat history for the default or requested session.

## `DELETE /api/history`

Clears process-local chat history.

## `POST /api/chat`

Request:

```json
{
  "message": "What should I check when users cannot log in after the latest deployment?",
  "session_id": "optional"
}
```

Response includes:

```json
{
  "answer": "...",
  "piter": {
    "priority": "...",
    "investigation": "...",
    "triage": "...",
    "escalation": "...",
    "resolution": "..."
  },
  "business_impact": "...",
  "next_action": "...",
  "confidence": "medium",
  "sources": [],
  "tool_results": [],
  "memory": {
    "last_question": "..."
  }
}
```

## `POST /api/incidents/analyze`

Request:

```json
{
  "alert_title": "High error rate on auth-service",
  "service": "auth-service",
  "environment": "production",
  "severity": "high",
  "description": "Many users cannot log in after the latest production deployment."
}
```

The endpoint returns the same normalized PITER fields plus tool outputs.
