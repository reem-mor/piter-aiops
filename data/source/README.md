# PITER AiOps Enterprise Demo Data

Canonical structured data for PITER AiOps.

- `alert_stream.csv`: 400 deterministic alerts for the alert-storm demo.
- `alerts.csv`: summarized investigation candidates.
- `deploys.csv`: deployment correlation data.
- `service_owners.csv`: sanitized service ownership metadata.
- `on_call_schedule.csv`: role-based on-call schedule without private contacts.
- `past_incidents.csv`: sanitized historical incidents.
- `business_impact.json`: sanitized business-impact model.
- `priority_matrix.json`: priority factors and thresholds.
- `escalation_policies.json`: escalation and notification safety policies.

Safety: no credentials, private phone numbers, raw emails, real customer data, or internal secrets. Real SNS/SES recipients must be configured outside Git.
