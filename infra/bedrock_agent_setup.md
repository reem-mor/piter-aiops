# Bedrock Agent Setup

Recommended agent name: `piter-aiops-incident-response-agent`.

Attach:

- Knowledge Base using S3 prefix `projects/piter-aiops/knowledge_base/`
- Action groups for recent deployments, service context, similar incidents, and escalation preview
- Guardrail that blocks secrets and unsafe notification behavior

After any change:

1. Prepare the draft agent.
2. Create a new version.
3. Update the live alias to the new version.
4. Put the live alias ID in `.env`.
