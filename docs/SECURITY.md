# Security and public documentation

This repo is **portfolio-public**. Do not commit:

- Live AWS account IDs, EC2 instance IDs, or public hostnames
- Bedrock agent/KB/data-source IDs from your account
- S3 bucket names tied to your account
- Email addresses, phone numbers, or IAM user names
- SES message IDs or SSM parameter values from production

## Use environment variables instead

Copy [`.env.example`](.env.example) and set values locally or in SSM/Parameter Store on deploy targets:

| Variable | Purpose |
| -------- | ------- |
| `AWS_ACCOUNT_ID` | IAM policy ARNs in docs/scripts |
| `PITER_DEMO_HOST` | EC2 public DNS for deploy/verify scripts |
| `PITER_EC2_INSTANCE_ID` | SSM/EC2 commands |
| `PITER_BEDROCK_*` | Agent, alias, KB, data source |
| `PITER_S3_BUCKET` | Knowledge-base sync |
| `PITER_ESCALATION_*` | Live notification recipients |

Operational scripts under `scripts/` that touch SSM/SES are **templates** — edit recipients in your private env before running against AWS.

## Before pushing

```powershell
rg -i "ec2-[0-9]|i-[0-9a-f]{8,}|@[a-z0-9.-]+\.(com|org|il)" --glob '!node_modules' .
```

If you find live identifiers, replace with placeholders and keep real values in gitignored `.env` only.
