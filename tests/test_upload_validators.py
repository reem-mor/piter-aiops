"""Upload filename and size validation."""
import pytest

from app.errors import BedrockError
from app.upload_validators import ALLOWED_UPLOAD_SUFFIXES, validate_upload_filename, validate_upload_size


def test_validate_filename_accepts_md():
    assert validate_upload_filename("runbook.md") == "runbook.md"


def test_validate_filename_rejects_missing():
    with pytest.raises(BedrockError) as exc:
        validate_upload_filename("")
    assert exc.value.code == "missing_file"


def test_validate_filename_rejects_exe():
    with pytest.raises(BedrockError) as exc:
        validate_upload_filename("malware.exe")
    assert exc.value.code == "unsupported_type"
    assert ".exe" in exc.value.user_message


@pytest.mark.parametrize("suffix", sorted(ALLOWED_UPLOAD_SUFFIXES))
def test_all_allowed_suffixes(suffix):
    assert validate_upload_filename(f"doc{suffix}") == f"doc{suffix}"


def test_validate_size_rejects_empty():
    with pytest.raises(BedrockError) as exc:
        validate_upload_size(0, max_bytes=1024)
    assert exc.value.code == "empty_file"


def test_validate_size_rejects_oversize():
    with pytest.raises(BedrockError) as exc:
        validate_upload_size(10_000, max_bytes=100)
    assert exc.value.code == "file_too_large"


def test_validate_filename_accepts_json():
    assert validate_upload_filename("config.json") == "config.json"


def test_validate_filename_rejects_path_traversal():
    with pytest.raises(BedrockError) as exc:
        validate_upload_filename("../../etc/passwd.json")
    assert exc.value.code == "invalid_filename"
