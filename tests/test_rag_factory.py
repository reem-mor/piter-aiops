"""Tests for RAG backend factory."""
from app.config import Config
from app.rag_factory import get_rag_client
from app.bedrock_client import BedrockRagClient
from app.bedrock_agent_client import BedrockAgentClient


def test_factory_returns_agent_client_by_default():
    cfg = Config(
        AWS_REGION="us-east-1",
        BEDROCK_KB_ID="kb",
        BEDROCK_MODEL_ARN="arn:aws:bedrock:::model/x",
        BEDROCK_NUM_RESULTS=5,
        SECRET_KEY="s",
        FLASK_ENV="testing",
        BEDROCK_AGENT_ID="a1",
        BEDROCK_AGENT_ALIAS_ID="al1",
        RAG_BACKEND="agent",
    )
    assert isinstance(get_rag_client(cfg), BedrockAgentClient)


def test_factory_returns_rag_client_for_legacy_backend():
    cfg = Config(
        AWS_REGION="us-east-1",
        BEDROCK_KB_ID="kb",
        BEDROCK_MODEL_ARN="arn:aws:bedrock:::model/x",
        BEDROCK_NUM_RESULTS=5,
        SECRET_KEY="s",
        FLASK_ENV="testing",
        RAG_BACKEND="retrieve_and_generate",
    )
    assert isinstance(get_rag_client(cfg), BedrockRagClient)
