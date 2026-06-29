# Knowledge Base Sync

Upload:

```powershell
aws s3 sync knowledge_base/ s3://<bucket-name>/projects/piter-aiops/knowledge_base/ --exclude "*.tmp" --exclude "__pycache__/*"
```

Then start ingestion from the Bedrock console or:

```powershell
python scripts/sync_knowledge_base.py
```

Verify ingestion completes and test retrieval for auth-service login failure, deployment rollback, Redis token store degradation, database connectivity, and API Gateway 5xx.
