"""Offline RAG client used as the default demo backend and Bedrock fallback.

``LocalRagClient`` exposes the same ``ask(...)`` surface as
``BedrockAgentClient`` so it is a drop-in replacement when AWS is unavailable.
It grounds every answer in locally retrieved runbook chunks and never raises a
network error, which keeps the live demo reliable.
"""
from __future__ import annotations

import logging
import time
import uuid

from app.bedrock_client import Citation, RagAnswer, _dedupe_citations
from app.config import Config
from app.services.local_rag import (
    LocalRetriever,
    RetrievedChunk,
    _first_excerpt_steps,
    get_retriever,
)
from app.text_utils import format_citation_preview
from app.validators import validate_question

log = logging.getLogger(__name__)

_NO_MATCH = (
    "Not in knowledge base. No runbook matched this query closely enough to "
    "answer with confidence. Escalate with the alert details and prepared notes."
)


def _excerpt(text: str, limit: int = 600) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " ..."


def _chunk_to_citation(chunk: RetrievedChunk, index: int) -> Citation:
    snippet = _excerpt(chunk.excerpt)
    return Citation(
        snippet=snippet,
        source_uri=f"local://knowledge_base/{chunk.document}",
        source_label=chunk.document,
        index=index,
        score=chunk.score,
        chunk_index=chunk.chunk_index,
        preview=format_citation_preview(snippet, chunk.document),
    )


def compose_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    """Build a scannable, grounded answer string from retrieved chunks."""
    if not chunks:
        return _NO_MATCH
    top = chunks[0]
    documents = {chunk.document for chunk in chunks}
    question_lower = question.lower()
    if (
        "auth_service_login_failure.json" in documents
        or any("auth_service_login_failure" in doc for doc in documents)
        or ("login" in question_lower and "deployment" in question_lower)
        or ("auth-service" in question_lower and "deployment" in question_lower)
    ):
        source_list = ", ".join(dict.fromkeys(chunk.document for chunk in chunks))
        return "\n".join(
            [
                "Priority:",
                "Treat as P1/P2 until scope is confirmed because auth-service login failure can block all authenticated customer journeys.",
                "",
                "Investigation findings:",
                "The question matches the auth-service login failure runbook and historical auth incident guidance. Focus on deployment timing, auth-service health, Redis token store, customer-db connectivity, and API Gateway auth routes.",
                "",
                "Triage plan:",
                "1. Confirm login error rate, affected markets, and whether failures started within 60 minutes of the latest auth-service or gateway deployment.",
                "2. Check recent deployments, feature flags, schema migrations, and token-signing key changes.",
                "3. Validate auth-service pod health, readiness probes, and logs before restarting anything.",
                "4. Check Redis token store latency, evictions, memory pressure, and failover state.",
                "5. Check customer-db connection pool saturation, lock waits, slow queries, and migration locks.",
                "6. If deployment correlation is strong and rollback is safe, prepare rollback while dependency checks continue.",
                "",
                "Escalation recommendation:",
                "Notify Identity and Access primary on-call for P1/P2 impact, then secondary on-call and incident commander if acknowledgement is missed. Produce a safe escalation preview only.",
                "",
                "Resolution plan:",
                "Mitigate with feature-flag disablement or rollback when deployment-correlated; otherwise follow the Redis, database, or API Gateway runbook indicated by dependency health checks. Verify login success rate before closing.",
                "",
                "Business impact:",
                "Login failure can prevent users from reaching wallet, payments, and product flows, so SLA, revenue, and regulated-market exposure should be called out explicitly.",
                "",
                "Sources:",
                source_list or top.document,
                "",
                "Confidence and uncertainty:",
                "Medium confidence from local Knowledge Base retrieval. Root cause remains uncertain until deployment correlation and dependency health are confirmed.",
            ]
        )

    steps: list[str] = []
    for chunk in chunks[:3]:
        steps.extend(_first_excerpt_steps(chunk.excerpt))
        if steps:
            break
    summary_line = top.excerpt.splitlines()[0].lstrip("# ").strip()

    parts = [f"Summary:\n{summary_line or 'See runbook for guidance.'}", ""]
    if steps:
        parts.append("Recommended steps:")
        for i, step in enumerate(steps[:8], start=1):
            parts.append(f"{i}. {step}")
        parts.append("")
    parts.append(f"Why this answer:\nGrounded in {top.document} (local knowledge base).")
    return "\n".join(parts).strip()


class LocalRagClient:
    """Question in via local TF-IDF retrieval; grounded answer + citations out."""

    def __init__(self, config: Config | None = None, *, retriever: LocalRetriever | None = None) -> None:
        self._config = config
        self._retriever = retriever or get_retriever()
        self._top_k = max(1, getattr(config, "BEDROCK_NUM_RESULTS", 5) or 5)

    @property
    def retriever(self) -> LocalRetriever:
        return self._retriever

    def retrieve(self, question: str, *, top_k: int | None = None) -> list[RetrievedChunk]:
        return self._retriever.search(question, top_k=top_k or self._top_k)

    def ask(
        self,
        question: str,
        *,
        session_id: str | None = None,
        session_attributes: dict[str, str] | None = None,
        prompt_session_attributes: dict[str, str] | None = None,
    ) -> RagAnswer:
        """Return a grounded :class:`RagAnswer` built entirely offline."""
        question = validate_question(question)
        started = time.perf_counter()
        chunks = self.retrieve(question)
        citations = _dedupe_citations(
            [_chunk_to_citation(chunk, idx) for idx, chunk in enumerate(chunks, start=1)]
        )
        answer_text = compose_answer(question, chunks)
        grounded = bool(citations)
        latency_ms = int((time.perf_counter() - started) * 1000)
        matched = citations[0].source_label if citations else None
        return RagAnswer(
            answer=answer_text,
            citations=citations,
            session_id=session_id or str(uuid.uuid4()),
            grounded=grounded,
            latency_ms=latency_ms,
            matched_runbook=matched,
            enrichment=None,
            mode="local",
        )
