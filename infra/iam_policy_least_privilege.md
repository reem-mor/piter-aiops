# IAM Least Privilege

Grant only what the demo needs. **No `admin-*` / `*:*` in the final posture.**

A ready-to-apply policy for the EC2 instance profile / app role is in
[`app_role_policy.json`](./app_role_policy.json) — replace the `<REGION>`,
`<ACCOUNT_ID>`, `<AGENT_ID>`, `<AGENT_ALIAS_ID>`, `<KB_ID>`, `<BUCKET>`, and
`<SES_SENDER_EMAIL>` placeholders, then attach it to the instance role.

## Flask / Demo Runtime (EC2 instance profile / app role)

- `bedrock:InvokeAgent` on the configured **agent alias ARN**.
- `bedrock:Retrieve` / `bedrock:RetrieveAndGenerate` on the **KB ARN** (direct KB fallback).
- `bedrock:InvokeModel` on the foundation model (required for RetrieveAndGenerate).
- `lambda:InvokeFunction` on the **four** action-group function ARNs only
  (piter-recent-deployments, piter-service-context, piter-similar-incidents, piter-escalation).
- `ses:SendEmail` (scoped to the verified sender via an `ses:FromAddress` condition).
- `sns:Publish` + `sms-voice:SendTextMessage` for the single SMS, plus read-only SMS readiness checks.
- CloudWatch Logs write (`/piter-aiops/*`).

No baked AWS keys — the instance uses the attached instance profile.

## Knowledge Base S3

- `s3:GetObject`
- `s3:ListBucket`

Scope resources to:

- `arn:aws:s3:::<bucket-name>`
- `arn:aws:s3:::<bucket-name>/projects/piter-aiops/knowledge_base/*`

## Lambda Action Groups

- Bedrock Agent role can invoke the specific action-group Lambda ARNs.
- Lambda execution role can write CloudWatch Logs.

Avoid administrator access as the final project posture.
