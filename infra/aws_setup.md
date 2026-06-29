# AWS Setup

Use one AWS account and region for the demo, preferably `us-east-1`.

Required resources:

- S3 bucket for Knowledge Base source files.
- Bedrock Knowledge Base with S3 data source.
- Bedrock Agent with Knowledge Base attachment.
- Lambda functions for action groups.
- IAM roles with least privilege.
- CloudWatch Logs for Lambda and agent troubleshooting.

Keep credentials in `~/.aws/credentials` or environment variables. Do not commit real secrets or private IDs.
