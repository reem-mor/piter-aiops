"""Unit tests for app.errors.translate()."""
from __future__ import annotations

from botocore.exceptions import BotoCoreError, ClientError

from app.errors import BedrockError, translate


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "boom"}}, "TestOperation")


def test_translate_maps_throttling():
    err = translate(_client_error("ThrottlingException"))
    assert isinstance(err, BedrockError)
    assert err.code == "ThrottlingException"
    assert "throttling" in err.user_message.lower()


def test_translate_maps_access_denied():
    err = translate(_client_error("AccessDenied"))
    assert err.code == "AccessDenied"
    assert "S3 denied" in err.user_message or "authorized" in err.user_message.lower()


def test_translate_maps_resource_not_found():
    err = translate(_client_error("ResourceNotFoundException"))
    assert err.code == "ResourceNotFoundException"
    assert "could not be found" in err.user_message.lower()


def test_translate_botocore_error():
    err = translate(BotoCoreError())
    assert err.code == "botocore_error"
    assert "reach AWS" in err.user_message


def test_translate_unknown_exception():
    err = translate(RuntimeError("unexpected"))
    assert err.code == "unknown"
    assert "Unexpected server error" in err.user_message
