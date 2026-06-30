"""Route tests for POST /documents/upload."""
from __future__ import annotations

import io
from dataclasses import replace

import pytest

from app.errors import BedrockError
from app.upload_service import DocumentUploadService, UploadResult


class _FakeUploadService:
    def __init__(self):
        self.next_result: UploadResult | None = None
        self.next_error: BedrockError | None = None
        self.calls: list[tuple[str | None, bytes, bool]] = []

    def upload(self, filename, body, *, sync_kb: bool):
        self.calls.append((filename, body, sync_kb))
        if self.next_error is not None:
            raise self.next_error
        return self.next_result


@pytest.fixture
def upload_service():
    return _FakeUploadService()


@pytest.fixture
def upload_app(app, upload_service):
    app.extensions["upload_service"] = upload_service
    app.config.update(
        S3_BUCKET="your-artifacts-bucket",
        S3_PREFIX="projects/piter-aiops/knowledge_base",
        BEDROCK_DATA_SOURCE_ID="${PITER_BEDROCK_DATA_SOURCE_ID}",
        MAX_UPLOAD_BYTES=1024,
    )
    return app


@pytest.fixture
def upload_client(upload_app):
    return upload_app.test_client()


def _file(name: str, content: bytes):
    return (io.BytesIO(content), name)


@pytest.fixture
def real_upload_app(app, fake_config):
    cfg = replace(fake_config, MAX_UPLOAD_BYTES=1024)
    app.extensions["upload_service"] = DocumentUploadService(cfg)
    return app


@pytest.fixture
def real_upload_client(real_upload_app):
    return real_upload_app.test_client()


def test_upload_missing_file_400(real_upload_client):
    resp = real_upload_client.post(
        "/documents/upload?format=json",
        data={},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["ok"] is False
    assert data["reason"] == "missing_file"


def test_upload_empty_file_400(real_upload_client):
    resp = real_upload_client.post(
        "/documents/upload?format=json",
        data={"document": _file("empty.txt", b"")},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["reason"] == "empty_file"


def test_upload_file_too_large_400(real_upload_client):
    resp = real_upload_client.post(
        "/documents/upload?format=json",
        data={"document": _file("big.txt", b"x" * 2048)},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["reason"] == "file_too_large"


def test_upload_success_json(upload_client, upload_service):
    upload_service.next_result = UploadResult(
        filename="note.txt",
        s3_key="projects/piter-aiops/knowledge_base/x_note.txt",
        s3_uri="s3://bucket/projects/piter-aiops/knowledge_base/x_note.txt",
        size_bytes=12,
        sync_started=True,
        ingestion_job_id="job-1",
    )
    resp = upload_client.post(
        "/documents/upload?format=json",
        data={"document": _file("note.txt", b"hello world"), "sync_kb": "on"},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["filename"] == "note.txt"
    assert data["ingestion_job_id"] == "job-1"
    assert upload_service.calls[0][2] is True


def test_upload_unsupported_type_400(upload_client, upload_service):
    upload_service.next_error = BedrockError("Unsupported", code="unsupported_type")
    resp = upload_client.post(
        "/documents/upload?format=json",
        data={"document": _file("bad.exe", b"x")},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["reason"] == "unsupported_type"


def test_upload_s3_error_502(upload_client, upload_service):
    upload_service.next_error = BedrockError("S3 denied", code="AccessDenied")
    resp = upload_client.post(
        "/documents/upload",
        data={"document": _file("note.txt", b"data")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 502


def test_upload_partial_sync_returns_202_json(upload_client, upload_service):
    upload_service.next_result = UploadResult(
        filename="a.txt",
        s3_key="prefix/key.txt",
        s3_uri="s3://test-bucket/prefix/key.txt",
        size_bytes=4,
        sync_started=False,
        sync_warning="File saved to s3://test-bucket/prefix/key.txt, but KB sync failed.",
    )
    resp = upload_client.post(
        "/documents/upload?format=json",
        data={"document": _file("a.txt", b"data"), "sync_kb": "true"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 202
    data = resp.get_json()
    assert data["ok"] is True
    assert data.get("partial") is True
    assert data.get("sync_warning")


def test_upload_json_format(upload_client, upload_service):
    upload_service.next_result = UploadResult(
        filename="a.md",
        s3_key="k",
        s3_uri="s3://b/k",
        size_bytes=3,
        sync_started=False,
    )
    resp = upload_client.post(
        "/documents/upload?format=json",
        data={"document": _file("a.md", b"# x")},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["filename"] == "a.md"


def test_upload_disabled_400(upload_client, upload_app, upload_service):
    upload_app.config["S3_BUCKET"] = ""
    upload_service.next_error = BedrockError("not configured", code="upload_disabled")
    resp = upload_client.post(
        "/documents/upload",
        data={"document": _file("a.txt", b"x")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
