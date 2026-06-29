"""Select RAG backend: local offline, Bedrock Agent, or direct RetrieveAndGenerate."""
from __future__ import annotations

from typing import Protocol

from app.services.bedrock_agent_service import get_agent_client
from app.bedrock_client import BedrockRagClient, RagAnswer
from app.config import Config
from app.local_agent import LocalRagClient


class RagClient(Protocol):
    def ask(self, question: str, *, session_id: str | None = None) -> RagAnswer: ...


def get_rag_client(config: Config, *, client: object | None = None) -> RagClient:
    """Pick the RAG backend from config.

    Local mode (``USE_BEDROCK=false`` or ``RAG_BACKEND=local``) needs no AWS and
    is the reliable demo default. Otherwise use the Bedrock Agent (default) or
    direct ``RetrieveAndGenerate``.
    """
    if not config.USE_BEDROCK or config.RAG_BACKEND == "local":
        return LocalRagClient(config)
    if config.RAG_BACKEND == "retrieve_and_generate":
        return BedrockRagClient(config, client=client)
    return get_agent_client(config, client=client)


def get_local_client(config: Config | None = None) -> LocalRagClient:
    """Return a local client for offline fallback when Bedrock fails."""
    return LocalRagClient(config)
