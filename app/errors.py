"""Map low-level boto3 errors to user-safe messages."""
from __future__ import annotations

from botocore.exceptions import BotoCoreError, ClientError, EventStreamError


class BedrockError(Exception):
    """Raised by BedrockRagClient for any user-presentable failure."""

    def __init__(self, user_message: str, *, code: str = "bedrock_error") -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.code = code


_FRIENDLY = {
    "ThrottlingException": "Bedrock is throttling requests. Please try again in a moment.",
    "AccessDeniedException": "The server is not authorized to call Bedrock. Check IAM permissions.",
    "ValidationException": "The Bedrock request was rejected as invalid. Try a shorter question.",
    "ResourceNotFoundException": "The configured Knowledge Base, Bedrock Agent, or model could not be found.",
    "DependencyFailedException": "A Bedrock dependency (model or action group) failed. Retry or check agent IAM and model access.",
    "ServiceQuotaExceededException": "A Bedrock service quota was exceeded.",
    "NoSuchBucket": "The configured S3 bucket does not exist.",
    "AccessDenied": "S3 denied the upload. Check bucket policy and IAM PutObject permissions.",
}
_FRIENDLY_LOWER = {k.lower(): v for k, v in _FRIENDLY.items()}


def translate(exc: Exception) -> BedrockError:
    if isinstance(exc, EventStreamError):
        code = "EventStreamError"
        if exc.response and isinstance(exc.response, dict):
            code = exc.response.get("Error", {}).get("Code", code)
        msg = _FRIENDLY_LOWER.get(code.lower(), "Bedrock returned an unexpected error.")
        return BedrockError(msg, code=code.lower())
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "ClientError")
        msg = _FRIENDLY_LOWER.get(code.lower(), "Bedrock returned an unexpected error.")
        return BedrockError(msg, code=code)
    if isinstance(exc, BotoCoreError):
        return BedrockError("Could not reach AWS Bedrock. Check network or credentials.", code="botocore_error")
    return BedrockError("Unexpected server error while calling Bedrock.", code="unknown")
