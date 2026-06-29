# AWS credentials for local and Docker runs

PITER AiOps uses the standard AWS credential chain:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`)
2. Shared credentials file (`~/.aws/credentials`)
3. SSO / IAM Identity Center profiles (`aws sso login --profile YOUR_PROFILE`)
4. EC2 instance profile (on the demo instance)

## Verify locally

```powershell
aws sts get-caller-identity
py -3.12 scripts/verify_credentials.py
```

## Docker Compose

Mount or pass credentials only for local Bedrock testing. Production demo on EC2 should use an **instance profile** — do not bake secrets into the image.

Copy `.env.example` to `.env` and set Bedrock IDs from the AWS console. See [`environment.md`](environment.md).

## Required IAM (summary)

| Use | Actions |
|-----|---------|
| Bedrock Agent | `bedrock:InvokeAgent` |
| Knowledge Base | `bedrock:Retrieve`, `bedrock:RetrieveAndGenerate` |
| KB sync (workstation) | `s3:PutObject`, `s3:ListBucket` on `projects/piter-aiops/knowledge_base/` |
| Agent deploy script | `bedrock:*` agent APIs, `lambda:*`, `iam:PassRole` |

Full EC2 checklist: [`ec2_deployment.md`](ec2_deployment.md).
