# EC2 Deployment — PITER AiOps

Public demo checklist for the mid-course presentation.

## AWS resources

| Resource | Purpose |
|----------|---------|
| EC2 (Amazon Linux 2023, t3.small+) | Runs Docker container on port 8080 |
| IAM instance profile | Bedrock InvokeAgent, KB retrieve, optional S3 read |
| S3 + prefix `projects/piter-aiops/knowledge_base/` | KB document source |
| Bedrock Knowledge Base + data source | RAG corpus |
| Bedrock Agent + **Prepared** alias | Primary inference path |
| 4 Lambda action groups | Deployments, service context, similar incidents, escalation preview |
| CloudWatch Logs | Lambda and app troubleshooting |
| Security group | SSH (22) from your IP; **8080** open for demo audience |

## Pre-deploy (from workstation)

```powershell
cd C:\dev\amdocs-ai-course\projects\piter-aiops
python scripts/verify_credentials.py
.\scripts\aws_deploy_fix.ps1
python scripts/sync_knowledge_base.py --ingest --wait
python scripts/agent_smoke_test.py
docker build -t piter-aiops:latest .
```

## Launch EC2 (example)

```powershell
aws ec2 run-instances `
  --image-id resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 `
  --instance-type t3.small `
  --key-name YOUR_KEY `
  --security-group-ids sg-XXXXXXXX `
  --subnet-id subnet-XXXXXXXX `
  --associate-public-ip-address `
  --iam-instance-profile Name=YOUR_BEDROCK_EC2_PROFILE `
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=piter-aiops-demo},{Key=Project,Value=piter-aiops}]"
```

Open security group **8080/tcp** to the classroom network or `0.0.0.0/0` for the demo window only.

## On the instance

```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

# Copy image or build from repo clone
docker run -d --name piter-aiops --restart unless-stopped -p 8080:8080 \
  -e PITER_USE_BEDROCK=true \
  -e RAG_BACKEND=agent \
  --env-file /opt/piter-aiops/.env \
  piter-aiops:latest

curl -s http://localhost:8080/health
curl -s http://localhost:8080/api/health?deep=1
```

Public URL: `http://<public-dns>:8080/` (SPA: `/#live-kb`, storm demo: `/#mvp`).

## Post-deploy validation

```powershell
aws ec2 describe-instances --filters "Name=tag:Project,Values=piter-aiops" "Name=instance-state-name,Values=running" `
  --query "Reservations[].Instances[].[InstanceId,PublicDnsName,State.Name]" --output table

aws s3 ls s3://YOUR_BUCKET/projects/piter-aiops/knowledge_base/ --recursive

aws bedrock-agent get-agent-alias --agent-id AGENT_ID --agent-alias-id ALIAS_ID

python scripts/verify_live_demo.py --base-url http://PUBLIC_DNS:8080
```

## Teardown

Terminate the demo instance when finished to avoid cost:

```powershell
aws ec2 terminate-instances --instance-ids i-xxxxxxxx
```

Record results in [`screenshots/deployment_validation.md`](../screenshots/deployment_validation.md).
