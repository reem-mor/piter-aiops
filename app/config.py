"""Typed config loaded from environment variables (with .env fallback)."""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Empty AWS_PROFILE breaks botocore (ProfileNotFound); unset so bearer/default chain works.
if not os.environ.get("AWS_PROFILE", "").strip():
    os.environ.pop("AWS_PROFILE", None)

_FALSE_VALUES = {"false", "0", "no", "off"}
_TRUE_VALUES = {"true", "1", "yes", "on"}
_DEFAULT_S3_PREFIX = "projects/piter-aiops/knowledge_base"


class ConfigError(RuntimeError):
    """Raised when required environment variables are missing or invalid."""


def _env(name: str, legacy: str | None = None, default: str = "") -> str:
    """Resolve PITER_-prefixed variable with optional legacy fallback."""
    piter_key = f"PITER_{name}" if not name.startswith("PITER_") else name
    value = os.environ.get(piter_key, "").strip()
    if not value and legacy:
        value = os.environ.get(legacy, "").strip()
    if not value:
        value = default
    return value


def _require(name: str, legacy: str | None = None) -> str:
    value = _env(name, legacy=legacy)
    if not value:
        label = f"PITER_{name}" if legacy is None else f"PITER_{name} or {legacy}"
        raise ConfigError(f"Missing required environment variable: {label}")
    return value


def _env_bool(name: str, default: bool, *, legacy: str | None = None) -> bool:
    raw = _env(name, legacy=legacy).lower()
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    return default


@dataclass(frozen=True)
class Config:
    AWS_REGION: str
    BEDROCK_KB_ID: str
    BEDROCK_MODEL_ARN: str
    BEDROCK_NUM_RESULTS: int
    SECRET_KEY: str
    FLASK_ENV: str
    S3_BUCKET: str = ""
    S3_PREFIX: str = _DEFAULT_S3_PREFIX
    BEDROCK_DATA_SOURCE_ID: str = ""
    MAX_UPLOAD_BYTES: int = 5_242_880
    BEDROCK_AGENT_ID: str = ""
    BEDROCK_AGENT_ALIAS_ID: str = ""
    RAG_BACKEND: str = "agent"
    USE_BEDROCK: bool = True
    MEMORY_ENABLED: bool = True
    LOCAL_FALLBACK: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        max_upload = _env("MAX_UPLOAD_BYTES", default="5242880")
        rag_backend = _env("RAG_BACKEND", legacy="RAG_BACKEND", default="agent").lower()
        if rag_backend not in ("agent", "retrieve_and_generate"):
            raise ConfigError(
                f"Invalid RAG_BACKEND={rag_backend!r}; use 'agent' or 'retrieve_and_generate'"
            )
        kb_id = (
            _env("BEDROCK_KB_ID", legacy="BEDROCK_KB_ID")
            or _env("KNOWLEDGE_BASE_ID", legacy="BEDROCK_KB_ID")
        )
        if not kb_id:
            raise ConfigError(
                "Missing required environment variable: PITER_BEDROCK_KB_ID "
                "(or PITER_KNOWLEDGE_BASE_ID / legacy BEDROCK_KB_ID)"
            )
        agent_id = _env("BEDROCK_AGENT_ID", legacy="BEDROCK_AGENT_ID")
        agent_alias = _env("BEDROCK_AGENT_ALIAS_ID", legacy="BEDROCK_AGENT_ALIAS_ID")
        if rag_backend == "agent" and (not agent_id or not agent_alias):
            raise ConfigError(
                "RAG_BACKEND=agent requires PITER_BEDROCK_AGENT_ID and "
                "PITER_BEDROCK_AGENT_ALIAS_ID (or legacy BEDROCK_AGENT_* vars)"
            )
        use_bedrock = _env_bool("USE_BEDROCK", True, legacy="USE_BEDROCK")
        if _env_bool("MOCK_MODE", False):
            use_bedrock = False
        return cls(
            AWS_REGION=_require("AWS_REGION", legacy="AWS_REGION"),
            BEDROCK_KB_ID=kb_id,
            BEDROCK_MODEL_ARN=_require("BEDROCK_MODEL_ARN", legacy="BEDROCK_MODEL_ARN"),
            BEDROCK_NUM_RESULTS=int(
                _env("BEDROCK_NUM_RESULTS", legacy="BEDROCK_NUM_RESULTS", default="5") or "5"
            ),
            SECRET_KEY=_require("FLASK_SECRET_KEY", legacy="FLASK_SECRET_KEY"),
            FLASK_ENV=_env("FLASK_ENV", legacy="FLASK_ENV", default="production"),
            S3_BUCKET=_env("S3_BUCKET", legacy="S3_BUCKET"),
            S3_PREFIX=_env("S3_PREFIX", legacy="S3_PREFIX", default=_DEFAULT_S3_PREFIX),
            BEDROCK_DATA_SOURCE_ID=_env(
                "BEDROCK_DATA_SOURCE_ID", legacy="BEDROCK_DATA_SOURCE_ID"
            ),
            MAX_UPLOAD_BYTES=int(max_upload or "5242880"),
            BEDROCK_AGENT_ID=agent_id,
            BEDROCK_AGENT_ALIAS_ID=agent_alias,
            RAG_BACKEND=rag_backend,
            USE_BEDROCK=use_bedrock,
            MEMORY_ENABLED=_env_bool("MEMORY_ENABLED", True),
            LOCAL_FALLBACK=_env_bool("LOCAL_FALLBACK", False, legacy="LOCAL_FALLBACK"),
        )

    @classmethod
    def local(cls) -> "Config":
        """Build an offline-safe config that never requires AWS credentials."""
        secret = _env("FLASK_SECRET_KEY", legacy="FLASK_SECRET_KEY") or (
            "dev-local-" + secrets.token_hex(16)
        )
        max_upload = _env("MAX_UPLOAD_BYTES", default="5242880")
        return cls(
            AWS_REGION=_env("AWS_REGION", legacy="AWS_REGION", default="us-east-1")
            or "us-east-1",
            BEDROCK_KB_ID=_env("BEDROCK_KB_ID", legacy="BEDROCK_KB_ID"),
            BEDROCK_MODEL_ARN=_env("BEDROCK_MODEL_ARN", legacy="BEDROCK_MODEL_ARN"),
            BEDROCK_NUM_RESULTS=int(
                _env("BEDROCK_NUM_RESULTS", legacy="BEDROCK_NUM_RESULTS", default="5") or "5"
            ),
            SECRET_KEY=secret,
            FLASK_ENV=_env("FLASK_ENV", legacy="FLASK_ENV", default="development"),
            S3_BUCKET=_env("S3_BUCKET", legacy="S3_BUCKET"),
            S3_PREFIX=_env("S3_PREFIX", legacy="S3_PREFIX", default=_DEFAULT_S3_PREFIX),
            BEDROCK_DATA_SOURCE_ID=_env(
                "BEDROCK_DATA_SOURCE_ID", legacy="BEDROCK_DATA_SOURCE_ID"
            ),
            MAX_UPLOAD_BYTES=int(max_upload or "5242880"),
            BEDROCK_AGENT_ID=_env("BEDROCK_AGENT_ID", legacy="BEDROCK_AGENT_ID"),
            BEDROCK_AGENT_ALIAS_ID=_env(
                "BEDROCK_AGENT_ALIAS_ID", legacy="BEDROCK_AGENT_ALIAS_ID"
            ),
            RAG_BACKEND="local",
            USE_BEDROCK=False,
            MEMORY_ENABLED=_env_bool("MEMORY_ENABLED", True),
            LOCAL_FALLBACK=_env_bool("LOCAL_FALLBACK", True, legacy="LOCAL_FALLBACK"),
        )
