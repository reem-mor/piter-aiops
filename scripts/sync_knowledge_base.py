#!/usr/bin/env python3
"""Sync knowledge_base/ (JSON + catalog CSV) to S3 and start KB ingestion."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import boto3  # noqa: E402

from app.config import Config  # noqa: E402
from app.services.kb_corpus import KB_ROOT  # noqa: E402

# Only narrative JSON documents belong in the KB prefix. Structured indexes
# (catalog.csv, structured_data_index.json) now live under docs/kb/ and are
# explicitly pruned from S3 below. Prefer scripts/kb_live.py (boto3, no CLI).
KB_SUFFIXES = (".json",)


def sync_corpus_to_s3(cfg: Config) -> int:
    """Upload knowledge_base/**/*.json and catalog.csv under cfg.S3_PREFIX (prune stale keys)."""
    if not cfg.S3_BUCKET:
        print("S3_BUCKET is required to sync knowledge base documents")
        return 1
    prefix = cfg.S3_PREFIX.rstrip("/") + "/"
    if not KB_ROOT.is_dir():
        print(f"Missing knowledge base directory: {KB_ROOT}")
        return 1

    import os
    import subprocess

    dest = f"s3://{cfg.S3_BUCKET}/{prefix}"
    cmd = [
        "aws",
        "s3",
        "sync",
        str(KB_ROOT),
        dest,
        "--exclude",
        "*",
        "--include",
        "*.json",
        "--delete",
    ]
    profile = os.environ.get("AWS_PROFILE", "").strip()
    if profile:
        cmd.extend(["--profile", profile])
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        return result.returncode
    print(f"Synced JSON/CSV corpus to {dest}")

    # Prune anything that is not a narrative JSON doc so the KB prefix stays
    # grounding-clean: legacy markdown, the structured CSV index, and the
    # structured_data_index.json that were previously synced here.
    rm_cmd = [
        "aws",
        "s3",
        "rm",
        dest,
        "--recursive",
        "--exclude",
        "*",
        "--include",
        "*.md",
        "--include",
        "*.csv",
        "--include",
        "structured_data_index.json",
    ]
    if profile:
        rm_cmd.extend(["--profile", profile])
    print("Running:", " ".join(rm_cmd))
    subprocess.run(rm_cmd, check=False)

    return 0


def start_ingestion(cfg: Config, *, wait: bool) -> int:
    if not cfg.BEDROCK_DATA_SOURCE_ID:
        print("BEDROCK_DATA_SOURCE_ID is required to start ingestion")
        return 1
    client = boto3.client("bedrock-agent", region_name=cfg.AWS_REGION)
    response = client.start_ingestion_job(
        knowledgeBaseId=cfg.BEDROCK_KB_ID,
        dataSourceId=cfg.BEDROCK_DATA_SOURCE_ID,
        description="PITER AiOps knowledge_base sync",
    )
    job = response["ingestionJob"]
    job_id = job["ingestionJobId"]
    status = job["status"]
    print(f"Started ingestion job {job_id} with status {status}")

    if not wait:
        return 0

    while status in {"STARTING", "IN_PROGRESS"}:
        time.sleep(5)
        detail = client.get_ingestion_job(
            knowledgeBaseId=cfg.BEDROCK_KB_ID,
            dataSourceId=cfg.BEDROCK_DATA_SOURCE_ID,
            ingestionJobId=job_id,
        )["ingestionJob"]
        status = detail["status"]
        print(f"Ingestion status: {status}")

    stats = client.get_ingestion_job(
        knowledgeBaseId=cfg.BEDROCK_KB_ID,
        dataSourceId=cfg.BEDROCK_DATA_SOURCE_ID,
        ingestionJobId=job_id,
    )["ingestionJob"].get("statistics", {})
    print(f"Ingestion statistics: {stats}")
    return 0 if status == "COMPLETE" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync PITER knowledge_base to S3 and ingest")
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Only start ingestion (assume S3 already has current corpus)",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Only upload JSON/CSV corpus to S3",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Poll until ingestion completes",
    )
    args = parser.parse_args()

    cfg = Config.from_env()
    if not args.skip_upload:
        code = sync_corpus_to_s3(cfg)
        if code != 0:
            return code
    if args.skip_ingest:
        return 0
    return start_ingestion(cfg, wait=args.wait)


if __name__ == "__main__":
    raise SystemExit(main())

