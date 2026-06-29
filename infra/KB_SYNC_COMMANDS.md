# Knowledge Base sync (approval-gated)

Local JSON is canonical for offline RAG. Bedrock KB indexes **Markdown on S3**.

## 1. Export JSON → Markdown (local)

```powershell
cd projects/piter-aiops
python scripts/export_kb_json_to_md.py
```

## 2. Upload to S3 (requires APPROVED)

```powershell
$env:AWS_PROFILE = "reemmor"
aws s3 sync knowledge_base/ s3://reem-amdocs-ai-artifacts-3331/projects/piter-aiops/knowledge_base/ `
  --exclude "*.json" --region us-east-1
```

## 3. Start ingestion job (requires APPROVED)

```powershell
aws bedrock-agent start-ingestion-job `
  --knowledge-base-id RBTJM6NIG9 `
  --data-source-id YICXAB6WOG `
  --region us-east-1 `
  --profile reemmor
```

Verify status:

```powershell
aws bedrock-agent list-ingestion-jobs `
  --knowledge-base-id RBTJM6NIG9 `
  --data-source-id YICXAB6WOG `
  --region us-east-1 `
  --profile reemmor
```
