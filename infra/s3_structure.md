# S3 Structure

Recommended prefix:

```text
s3://<bucket-name>/projects/piter-aiops/knowledge_base/
```

Upload only:

- `knowledge_base/runbooks/*.md`
- `knowledge_base/incidents/*.md`
- `knowledge_base/services/*.md`
- `knowledge_base/escalation/*.md`
- `knowledge_base/business_impact/*.md`
- `knowledge_base/piter/*.md`

Exclude:

- caches
- screenshots
- tests
- local `.env`
- generated logs
- unrelated datasets
