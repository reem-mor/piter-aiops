"""Validate user document uploads before S3 / Bedrock ingestion."""
from __future__ import annotations

from pathlib import Path

from app.errors import BedrockError

ALLOWED_UPLOAD_SUFFIXES = frozenset({".md", ".txt", ".csv", ".docx", ".pdf", ".json"})


def validate_upload_filename(filename: str | None) -> str:
    name = (filename or "").strip()
    if not name:
        raise BedrockError("Choose a file to upload.", code="missing_file")
    if ".." in name or name != Path(name).name:
        raise BedrockError("Invalid filename.", code="invalid_filename")
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_SUFFIXES))
        raise BedrockError(
            f"Unsupported file type '{suffix or '(none)'}'. Allowed: {allowed}.",
            code="unsupported_type",
        )
    return name


def validate_upload_size(size: int, *, max_bytes: int) -> None:
    if size <= 0:
        raise BedrockError("File is empty.", code="empty_file")
    if size > max_bytes:
        mb = max(1, max_bytes // (1024 * 1024))
        raise BedrockError(f"File is too large. Maximum size is {mb} MB.", code="file_too_large")
