#!/usr/bin/env python3
"""PITER AiOps — Bedrock Knowledge Base live operations (boto3 only, no aws CLI).

Best-practice, audit-first lifecycle for the KB whose content lives under
``knowledge_base/`` and is synced to ``s3://$S3_BUCKET/$S3_PREFIX``:

    audit    (default, READ-ONLY) — verify identity, discover the KB + data
             source, print the configured S3 prefix, and list what is currently
             ingested. Changes nothing.
    sync     — upload ONLY the narrative KB docs (runbooks/services/incidents/
             piter guides) under the exact prefix and prune stale keys. Refuses
             to upload structured indexes (catalog.csv, structured_data_index.json)
             or anything outside the doc set, so the KB stays grounding-clean.
    ingest   — start an ingestion job and wait for COMPLETE; print statistics
             and the final ingested object list.
    verify   — run one in-KB query (expect a grounded, cited answer) and one
             out-of-KB query (expect an explicit "I don't know").

Configuration comes from the environment (PITER_* with legacy fallbacks):
    AWS_REGION (default us-east-1)
    PITER_S3_BUCKET, PITER_S3_PREFIX (default projects/piter-aiops/knowledge_base)
    PITER_BEDROCK_KB_ID, PITER_BEDROCK_DATA_SOURCE_ID  (auto-discovered if unset)
    PITER_BEDROCK_MODEL_ARN  (for verify / RetrieveAndGenerate)

Credentials use the default boto3 chain (env vars, shared config, or the EC2
instance profile). AWS_PROFILE is honored when set.

Usage:
    python scripts/kb_live.py audit
    python scripts/kb_live.py sync
    python scripts/kb_live.py ingest --wait
    python scripts/kb_live.py verify
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import boto3  # noqa: E402
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError  # noqa: E402

KB_ROOT = ROOT / "knowledge_base"

# Narrative document subtrees that belong in the KB (grounding content).
DOC_SUBDIRS = ("runbooks", "services", "incidents", "piter")
DOC_SUFFIXES = (".md",)
# Pure structured indexes that must NEVER be ingested (pollute retrieval).
FORBIDDEN_NAMES = {"catalog.csv", "structured_data_index.json"}
FORBIDDEN_SUFFIXES = {".csv", ".tar", ".json"}


def _env(name: str, default: str = "") -> str:
    return (
        os.environ.get(f"PITER_{name}", "").strip()
        or os.environ.get(name, "").strip()
        or default
    )


def _region() -> str:
    return _env("AWS_REGION", "us-east-1")


def _prefix() -> str:
    return _env("S3_PREFIX", "projects/piter-aiops/knowledge_base").rstrip("/") + "/"


def _local_doc_files() -> list[Path]:
    """Return the narrative KB docs eligible for upload (best-practice filter)."""
    files: list[Path] = []
    for sub in DOC_SUBDIRS:
        base = KB_ROOT / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
                continue
            if path.suffix.lower() in DOC_SUFFIXES:
                files.append(path)
    return files


def _session() -> boto3.session.Session:
    profile = os.environ.get("AWS_PROFILE", "").strip()
    return boto3.session.Session(profile_name=profile) if profile else boto3.session.Session()


def _whoami(sess: boto3.session.Session) -> str:
    ident = sess.client("sts", region_name=_region()).get_caller_identity()
    return ident["Arn"]


def _discover_kb(sess: boto3.session.Session) -> tuple[str, str, str, str]:
    """Resolve (kb_id, data_source_id, bucket, prefix), preferring env, else discovery."""
    agent = sess.client("bedrock-agent", region_name=_region())
    kb_id = _env("BEDROCK_KB_ID")
    if not kb_id:
        for kb in agent.list_knowledge_bases(maxResults=100).get("knowledgeBaseSummaries", []):
            if "piter" in kb["name"].lower():
                kb_id = kb["knowledgeBaseId"]
                break
    if not kb_id:
        raise SystemExit("Could not resolve a PITER knowledge base; set PITER_BEDROCK_KB_ID.")

    ds_id = _env("BEDROCK_DATA_SOURCE_ID")
    bucket = _env("S3_BUCKET")
    prefix = _prefix()
    sources = agent.list_data_sources(knowledgeBaseId=kb_id, maxResults=100)
    summaries = sources.get("dataSourceSummaries", [])
    if not ds_id and summaries:
        ds_id = summaries[0]["dataSourceId"]
    if ds_id:
        ds = agent.get_data_source(knowledgeBaseId=kb_id, dataSourceId=ds_id)["dataSource"]
        s3 = ds.get("dataSourceConfiguration", {}).get("s3Configuration", {})
        arn = s3.get("bucketArn", "")
        if arn and not bucket:
            bucket = arn.split(":")[-1]
        configured_prefixes = s3.get("inclusionPrefixes") or []
        if configured_prefixes:
            print(f"  data source inclusionPrefixes: {configured_prefixes}")
            if prefix.rstrip('/') not in [p.rstrip('/') for p in configured_prefixes]:
                print(
                    f"  WARNING: configured prefix {configured_prefixes} != expected {prefix!r}"
                )
    return kb_id, ds_id, bucket, prefix


def _list_s3(sess: boto3.session.Session, bucket: str, prefix: str) -> list[str]:
    s3 = sess.client("s3", region_name=_region())
    keys: list[str] = []
    token = None
    while True:
        kw = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kw["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kw)
        keys.extend(obj["Key"] for obj in resp.get("Contents", []))
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return keys


def cmd_audit(sess: boto3.session.Session) -> int:
    print(f"Identity: {_whoami(sess)}")
    print(f"Region:   {_region()}")
    kb_id, ds_id, bucket, prefix = _discover_kb(sess)
    print(f"KB id:        {kb_id}")
    print(f"Data source:  {ds_id}")
    print(f"S3:           s3://{bucket}/{prefix}")
    local = _local_doc_files()
    print(f"\nLocal narrative docs eligible for KB ({len(local)}):")
    for path in local:
        print(f"  {path.relative_to(KB_ROOT)}")
    if not bucket:
        print("\n(no bucket resolved; set PITER_S3_BUCKET to list S3 objects)")
        return 0
    s3_keys = _list_s3(sess, bucket, prefix)
    print(f"\nCurrently under the KB prefix in S3 ({len(s3_keys)}):")
    for key in s3_keys:
        flag = "  <-- FORBIDDEN" if (
            Path(key).name in FORBIDDEN_NAMES or Path(key).suffix.lower() in FORBIDDEN_SUFFIXES
        ) else ""
        print(f"  {key}{flag}")
    return 0


def cmd_sync(sess: boto3.session.Session) -> int:
    kb_id, ds_id, bucket, prefix = _discover_kb(sess)
    if not bucket:
        raise SystemExit("PITER_S3_BUCKET is required to sync.")
    s3 = sess.client("s3", region_name=_region())
    local = _local_doc_files()
    wanted = {f"{prefix}{path.relative_to(KB_ROOT).as_posix()}": path for path in local}

    print(f"Uploading {len(wanted)} narrative docs to s3://{bucket}/{prefix} ...")
    for key, path in sorted(wanted.items()):
        s3.upload_file(str(path), bucket, key)
        print(f"  put {key}")

    existing = set(_list_s3(sess, bucket, prefix))
    stale = sorted(existing - set(wanted))
    for key in stale:
        s3.delete_object(Bucket=bucket, Key=key)
        print(f"  pruned {key}")
    print("Sync complete (KB prefix now holds only narrative docs).")
    return 0


def cmd_ingest(sess: boto3.session.Session, *, wait: bool) -> int:
    kb_id, ds_id, bucket, prefix = _discover_kb(sess)
    if not ds_id:
        raise SystemExit("PITER_BEDROCK_DATA_SOURCE_ID is required to ingest.")
    agent = sess.client("bedrock-agent", region_name=_region())
    job = agent.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id,
        description="PITER AiOps KB sync (kb_live.py)",
    )["ingestionJob"]
    job_id, status = job["ingestionJobId"], job["status"]
    print(f"Started ingestion job {job_id}: {status}")
    while wait and status in {"STARTING", "IN_PROGRESS"}:
        time.sleep(5)
        job = agent.get_ingestion_job(
            knowledgeBaseId=kb_id, dataSourceId=ds_id, ingestionJobId=job_id
        )["ingestionJob"]
        status = job["status"]
        print(f"  status: {status}")
    print(f"Final status: {status}")
    print(f"Statistics: {job.get('statistics', {})}")
    if bucket:
        print("\nIngested object list (S3 prefix):")
        for key in _list_s3(sess, bucket, prefix):
            print(f"  {key}")
    return 0 if status == "COMPLETE" else 1


def cmd_verify(sess: boto3.session.Session) -> int:
    kb_id, ds_id, bucket, prefix = _discover_kb(sess)
    model_arn = _env("BEDROCK_MODEL_ARN")
    if not model_arn:
        raise SystemExit("PITER_BEDROCK_MODEL_ARN is required to verify.")
    rt = sess.client("bedrock-agent-runtime", region_name=_region())

    def _ask(question: str) -> tuple[str, int]:
        resp = rt.retrieve_and_generate(
            input={"text": question},
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": kb_id,
                    "modelArn": model_arn,
                },
            },
        )
        text = resp.get("output", {}).get("text", "")
        cites = sum(len(c.get("retrievedReferences", [])) for c in resp.get("citations", []))
        return text, cites

    in_kb = "What are the remediation steps for an auth-service login failure?"
    out_kb = "What is the capital of France according to the runbooks?"
    a1, c1 = _ask(in_kb)
    print(f"[in-KB] cited_refs={c1}\n{a1}\n")
    a2, c2 = _ask(out_kb)
    print(f"[out-of-KB] cited_refs={c2}\n{a2}\n")
    grounded = c1 > 0
    refused = (
        "don't know" in a2.lower()
        or "do not know" in a2.lower()
        or "no information" in a2.lower()
        or "cannot find" in a2.lower()
        or "can't find" in a2.lower()
        or "not in the knowledge base" in a2.lower()
        or c2 == 0
    )
    print(f"RESULT: grounded_in_kb={grounded}  refuses_out_of_kb={refused}")
    return 0 if (grounded and refused) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "sync", "ingest", "verify"], nargs="?", default="audit")
    parser.add_argument("--wait", action="store_true", help="ingest: poll until COMPLETE")
    args = parser.parse_args()

    try:
        sess = _session()
        sess.get_credentials() or sys.exit("No AWS credentials found (default chain empty).")
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        return f"AWS access error: {exc}"  # type: ignore[return-value]

    return {
        "audit": lambda: cmd_audit(sess),
        "sync": lambda: cmd_sync(sess),
        "ingest": lambda: cmd_ingest(sess, wait=args.wait),
        "verify": lambda: cmd_verify(sess),
    }[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
