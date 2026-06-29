"""Shared pytest fixtures: build a Flask app with a fake Bedrock client."""
from __future__ import annotations

import pytest

from app import create_app
from app.config import Config


class _FakeBedrockClient:
    """Fake BedrockRagClient that returns canned responses, controlled per-test."""

    def __init__(self):
        self.next_response = None
        self.next_error = None
        self.calls: list[str] = []

    def ask(
        self,
        question: str,
        *,
        session_id: str | None = None,
        session_attributes: dict | None = None,
        prompt_session_attributes: dict | None = None,
    ):
        self.calls.append(question)
        self.last_session_id = session_id
        self.last_session_attributes = session_attributes
        self.last_prompt_session_attributes = prompt_session_attributes
        if self.next_error is not None:
            raise self.next_error
        return self.next_response


@pytest.fixture(autouse=True)
def _isolate_chat_history(tmp_path):
    """Point the persistent chat-history store at a per-test temp file."""
    from app.services import chat_history
    from app.services import session_memory

    chat_history.set_store_path(tmp_path / "chat_history.json")
    session_memory.set_store_path(tmp_path / "session_memory.json")
    chat_history.reset()
    session_memory.reset()
    yield
    chat_history.reset()
    session_memory.reset()


@pytest.fixture
def fake_config():
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
        MAX_UPLOAD_BYTES=5242880,
        BEDROCK_AGENT_ID="agent-test",
        BEDROCK_AGENT_ALIAS_ID="alias-test",
        RAG_BACKEND="agent",
    )


@pytest.fixture
def fake_bedrock():
    return _FakeBedrockClient()


@pytest.fixture
def app(fake_config, fake_bedrock):
    app = create_app(fake_config)
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        FORCE_LEGACY_UI=False,
        LOCAL_FALLBACK=False,
    )
    app.extensions["bedrock_client"] = fake_bedrock
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def local_config():
    """Offline config that uses the local TF-IDF RAG backend (no AWS)."""
    return Config.local()


@pytest.fixture
def local_app(local_config):
    app = create_app(local_config)
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, FORCE_LEGACY_UI=True)
    return app


@pytest.fixture
def local_client(local_app):
    return local_app.test_client()
