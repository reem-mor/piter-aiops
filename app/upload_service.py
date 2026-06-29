"""Upload runbook documents to S3 and optionally trigger Bedrock KB sync."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from werkzeug.utils import secure_filename

from app.config import Config
from app.errors import BedrockError, translate
from app.upload_validators import validate_upload_filename, validate_upload_size

log = logging.getLogger(__name__)

_SAFE_KEY = re.compile(r"[^a-zA-Z0-9._-]+")


@dataclass(frozen=True)
class UploadResult:
    filename: str
    s3_key: str
    s3_uri: str
    size_bytes: int
    sync_started: bool
    ingestion_job_id: str | None = None
    sync_warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "filename": self.filename,
            "s3_key": self.s3_key,
            "s3_uri": self.s3_uri,
            "size_bytes": self.size_bytes,
            "sync_started": self.sync_started,
            "ingestion_job_id": self.ingestion_job_id,
        }
        if self.sync_warning:
            payload["sync_warning"] = self.sync_warning
            payload["partial"] = True
        return payload


def _object_key(prefix: str, filename: str) -> tuple[str, str]:
    safe = secure_filename(filename) or "document"
    safe = _SAFE_KEY.sub("_", safe)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    key = f"{prefix.rstrip('/')}/{stamp}_{safe}"
    return key, safe


class DocumentUploadService:
    def __init__(
        self,
        config: Config,
        *,
        s3_client=None,
        bedrock_agent_client=None,
    ) -> None:
        self._config = config
        self._s3 = s3_client or boto3.client("s3", region_name=config.AWS_REGION)
        self._agent = bedrock_agent_client or boto3.client(
            "bedrock-agent", region_name=config.AWS_REGION
        )

    def upload(self, filename: str | None, body: bytes, *, sync_kb: bool) -> UploadResult:
        if not self._config.S3_BUCKET:
            raise BedrockError(
                "Document upload is not configured (set S3_BUCKET in the environment).",
                code="upload_disabled",
            )

        original = validate_upload_filename(filename)
        validate_upload_size(len(body), max_bytes=self._config.MAX_UPLOAD_BYTES)

        key, _ = _object_key(self._config.S3_PREFIX, original)
        bucket = self._config.S3_BUCKET

        try:
            self._s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType=_content_type(original),
            )
        except (ClientError, BotoCoreError) as exc:
            log.warning("S3 upload failed: %s", exc)
            raise translate(exc) from exc

        s3_uri = f"s3://{bucket}/{key}"
        ingestion_job_id: str | None = None
        sync_started = False

        sync_warning: str | None = None
        if sync_kb:
            if not self._config.BEDROCK_DATA_SOURCE_ID:
                sync_warning = (
                    f"File saved to {s3_uri}, but KB sync is not configured "
                    "(set BEDROCK_DATA_SOURCE_ID). Sync manually in the Bedrock console."
                )
            else:
                try:
                    resp = self._agent.start_ingestion_job(
                        knowledgeBaseId=self._config.BEDROCK_KB_ID,
                        dataSourceId=self._config.BEDROCK_DATA_SOURCE_ID,
                        description=f"Web upload: {original}",
                    )
                    job = resp.get("ingestionJob") or {}
                    ingestion_job_id = job.get("ingestionJobId")
                    sync_started = True
                except (ClientError, BotoCoreError) as exc:
                    log.warning("KB sync failed after S3 upload: %s", exc)
                    err = translate(exc)
                    sync_warning = (
                        f"File saved to {s3_uri}, but Knowledge Base sync failed: {err.user_message}"
                    )

        return UploadResult(
            filename=original,
            s3_key=key,
            s3_uri=s3_uri,
            size_bytes=len(body),
            sync_started=sync_started,
            ingestion_job_id=ingestion_job_id,
            sync_warning=sync_warning,
        )


def _content_type(filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower()
    return {
        "md": "text/markdown",
        "txt": "text/plain",
        "csv": "text/csv",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(suffix, "application/octet-stream")
