"""Unit tests for DocumentUploadService using botocore Stubber."""
from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import replace
from unittest.mock import patch

import boto3
import pytest
from botocore.stub import Stubber

from app.config import Config
from app.errors import BedrockError
from app.upload_service import DocumentUploadService, _object_key


@pytest.fixture
def upload_config():
    return Config(
        AWS_REGION="us-east-1",
        BEDROCK_KB_ID="kb-test",
        BEDROCK_MODEL_ARN="arn:aws:bedrock:us-east-1::foundation-model/test",
        BEDROCK_NUM_RESULTS=5,
        SECRET_KEY="test-secret",
        FLASK_ENV="testing",
        S3_BUCKET="test-bucket",
        S3_PREFIX="projects/piter-aiops/knowledge_base",
        BEDROCK_DATA_SOURCE_ID="ds-test",
        MAX_UPLOAD_BYTES=1024,
    )


def test_object_key_prefixes_timestamp_and_sanitizes():
    fixed = datetime(2026, 5, 31, 12, 0, 0, tzinfo=UTC)
    with patch("app.upload_service.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        mock_dt.UTC = UTC
        key, safe = _object_key("prefix/path", "run book.md")
    assert safe == "run_book.md"
    assert key == "prefix/path/20260531T120000Z_run_book.md"


def test_upload_puts_object_without_sync(upload_config):
    s3 = boto3.client("s3", region_name=upload_config.AWS_REGION)
    s3_stub = Stubber(s3)
    s3_stub.add_response("put_object", {})

    service = DocumentUploadService(upload_config, s3_client=s3, bedrock_agent_client=None)
    with s3_stub:
        result = service.upload("note.txt", b"hello", sync_kb=False)

    assert result.filename == "note.txt"
    assert result.size_bytes == 5
    assert result.s3_uri.startswith("s3://test-bucket/")
    assert result.sync_started is False
    assert result.ingestion_job_id is None


def test_upload_starts_ingestion_job_when_sync_requested(upload_config):
    s3 = boto3.client("s3", region_name=upload_config.AWS_REGION)
    agent = boto3.client("bedrock-agent", region_name=upload_config.AWS_REGION)
    s3_stub = Stubber(s3)
    agent_stub = Stubber(agent)
    s3_stub.add_response("put_object", {})
    agent_stub.add_response(
        "start_ingestion_job",
        {
            "ingestionJob": {
                "ingestionJobId": "job-abc123",
                "knowledgeBaseId": upload_config.BEDROCK_KB_ID,
                "dataSourceId": upload_config.BEDROCK_DATA_SOURCE_ID,
                "status": "STARTING",
                "startedAt": datetime(2026, 5, 31, 12, 0, 0, tzinfo=UTC),
                "updatedAt": datetime(2026, 5, 31, 12, 0, 0, tzinfo=UTC),
            }
        },
    )

    service = DocumentUploadService(upload_config, s3_client=s3, bedrock_agent_client=agent)
    with s3_stub, agent_stub:
        result = service.upload("runbook.md", b"# title", sync_kb=True)

    assert result.sync_started is True
    assert result.ingestion_job_id == "job-abc123"


def test_upload_disabled_without_bucket(upload_config):
    cfg = replace(upload_config, S3_BUCKET="")
    service = DocumentUploadService(cfg, s3_client=boto3.client("s3", region_name="us-east-1"))
    with pytest.raises(BedrockError) as exc:
        service.upload("a.txt", b"x", sync_kb=False)
    assert exc.value.code == "upload_disabled"


def test_upload_kb_sync_not_configured_after_s3_put(upload_config):
    cfg = replace(upload_config, BEDROCK_DATA_SOURCE_ID="")
    s3 = boto3.client("s3", region_name=cfg.AWS_REGION)
    s3_stub = Stubber(s3)
    s3_stub.add_response("put_object", {})

    service = DocumentUploadService(cfg, s3_client=s3, bedrock_agent_client=None)
    with s3_stub:
        result = service.upload("a.txt", b"data", sync_kb=True)
    assert result.sync_started is False
    assert result.sync_warning
    assert "s3://" in result.sync_warning


def test_upload_maps_s3_client_error(upload_config):
    s3 = boto3.client("s3", region_name=upload_config.AWS_REGION)
    s3_stub = Stubber(s3)
    s3_stub.add_client_error("put_object", service_error_code="AccessDenied")

    service = DocumentUploadService(upload_config, s3_client=s3, bedrock_agent_client=None)
    with s3_stub:
        with pytest.raises(BedrockError) as exc:
            service.upload("a.txt", b"data", sync_kb=False)
    assert exc.value.code == "AccessDenied"
