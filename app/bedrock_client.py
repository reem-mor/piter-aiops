"""Thin boto3 wrapper around Bedrock Knowledge Base RetrieveAndGenerate."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config as BotoConfig

from app.config import Config
from app.errors import translate
from app.text_utils import (
    extract_reference_metadata,
    format_answer_sections,
    format_citation_label,
    format_citation_preview,
)
from app.validators import MAX_QUESTION_LEN, validate_question  # noqa: F401  (MAX_QUESTION_LEN re-exported for tests)

log = logging.getLogger(__name__)

# Re-export for templates and tests that import from bedrock_client.
MIN_QUESTION_LEN = 3

# Override Bedrock default prompt (which can nudge models toward tool-style output).
RAG_GENERATION_PROMPT = """You are PITER Ops, an enterprise incident-response assistant. Answer ONLY using the search results below.
Write plain English. Do NOT emit tool calls, JSON, or lines starting with "Action:".

Use exactly this structure:

Priority:
Classify P1-P4 with brief rationale (customer impact, service, environment, SLA risk).

Investigation findings:
What the evidence shows — logs, deployments, runbooks, similar incidents.

Triage plan:
1. First concrete check or action
2. Second action
(continue numbering as needed)

Escalation recommendation:
- When to escalate
- Who to escalate to (only if evidence supports it; otherwise state missing data)

Resolution plan:
Validation steps and safe recovery path.

Business impact:
Revenue, SLA, or customer-trust impact if supported by evidence.

Sources:
Cite runbook, alert history, or postmortem from the search results.

Confidence and uncertainty:
State confidence level and any missing evidence.

User question:
$query$

Search results:
$search_results$

$output_format_instructions$
"""


@dataclass(frozen=True)
class Citation:
    snippet: str
    source_uri: str | None
    source_label: str = "Unknown source"
    index: int = 1
    score: float | None = None
    chunk_index: int | None = None
    preview: str = ""

    def __post_init__(self) -> None:
        if self.source_uri and self.source_label == "Unknown source":
            object.__setattr__(
                self, "source_label", format_citation_label(self.source_uri)
            )
        if not self.preview and self.snippet:
            object.__setattr__(
                self,
                "preview",
                format_citation_preview(self.snippet, self.source_label),
            )


@dataclass(frozen=True)
class RagAnswer:
    answer: str
    citations: list[Citation]
    session_id: str | None
    grounded: bool
    latency_ms: int = 0
    matched_runbook: str | None = None
    enrichment: dict[str, Any] | None = None
    mode: str = "bedrock"
    fallback_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        sections = format_answer_sections(self.answer)
        payload: dict[str, Any] = {
            "answer": self.answer,
            "answer_sections": sections,
            "piter_sections": sections.get("piter_sections"),
            "citations": [
                {
                    "snippet": c.snippet,
                    "source_uri": c.source_uri,
                    "source_label": c.source_label,
                    "index": c.index,
                    "score": c.score,
                    "chunk_index": c.chunk_index,
                    "preview": c.preview or format_citation_preview(c.snippet, c.source_label),
                }
                for c in self.citations
            ],
            "session_id": self.session_id,
            "grounded": self.grounded,
            "latency_ms": self.latency_ms,
            "matched_runbook": self.matched_runbook,
            "mode": self.mode,
            "fallback_used": self.fallback_used,
        }
        if self.enrichment is not None:
            payload["enrichment"] = self.enrichment
        return payload


class BedrockRagClient:
    """One call: question in, grounded answer + citations out."""

    def __init__(self, config: Config, *, client: Any | None = None) -> None:
        self._config = config
        boto_cfg = BotoConfig(
            read_timeout=120,
            connect_timeout=10,
            retries={"max_attempts": 3, "mode": "standard"},
        )
        self._client = client or boto3.client(
            "bedrock-agent-runtime",
            region_name=config.AWS_REGION,
            config=boto_cfg,
        )

    def ask(self, question: str, *, session_id: str | None = None) -> RagAnswer:
        question = validate_question(question)
        started = time.perf_counter()
        request: dict[str, Any] = {
            "input": {"text": question},
            "retrieveAndGenerateConfiguration": {
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseId": self._config.BEDROCK_KB_ID,
                    "modelArn": self._config.BEDROCK_MODEL_ARN,
                    "retrievalConfiguration": {
                        "vectorSearchConfiguration": {
                            "numberOfResults": self._config.BEDROCK_NUM_RESULTS,
                        },
                    },
                    "generationConfiguration": {
                        "promptTemplate": {
                            "textPromptTemplate": RAG_GENERATION_PROMPT,
                        },
                        "inferenceConfig": {
                            # Claude (Haiku 4.5+) rejects sending both temperature
                            # and topP. For deterministic RAG we pin temperature=0
                            # and omit topP entirely.
                            "textInferenceConfig": {
                                "temperature": 0.0,
                                "maxTokens": 1024,
                                "stopSequences": ["Action:", "GlobalDataSource"],
                            },
                        },
                    },
                },
            },
        }
        if session_id:
            request["sessionId"] = session_id
        try:
            response = self._client.retrieve_and_generate(**request)
        except Exception as exc:  # noqa: BLE001 — funneled through translate()
            log.warning("Bedrock retrieve_and_generate failed: %s", exc)
            raise translate(exc) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        return _parse_response(response, latency_ms=latency_ms)


def _parse_response(response: dict[str, Any], *, latency_ms: int) -> RagAnswer:
    answer_text = (response.get("output", {}) or {}).get("text", "").strip()
    citations_raw = response.get("citations", []) or []

    parsed: list[Citation] = []
    for citation in citations_raw:
        for ref in citation.get("retrievedReferences", []) or []:
            snippet = (ref.get("content", {}) or {}).get("text", "").strip()
            location = ref.get("location", {}) or {}
            source_uri = (location.get("s3Location", {}) or {}).get("uri")
            if snippet:
                label = format_citation_label(source_uri)
                score, chunk_index = extract_reference_metadata(ref)
                parsed.append(
                    Citation(
                        snippet=snippet,
                        source_uri=source_uri,
                        source_label=label,
                        score=score,
                        chunk_index=chunk_index,
                        preview=format_citation_preview(snippet, label),
                    ),
                )

    citations = _dedupe_citations(parsed)
    grounded = bool(citations)
    if not grounded and not answer_text:
        answer_text = "I could not find anything in the knowledge base for that question."

    matched = citations[0].source_label if citations else None
    return RagAnswer(
        answer=answer_text,
        citations=citations,
        session_id=response.get("sessionId"),
        grounded=grounded,
        latency_ms=latency_ms,
        matched_runbook=matched,
    )


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    seen: set[tuple[str | None, str]] = set()
    unique: list[Citation] = []
    for citation in citations:
        key = (citation.source_uri, citation.snippet[:80])
        if key in seen:
            continue
        seen.add(key)
        unique.append(citation)
    return [
        Citation(
            snippet=c.snippet,
            source_uri=c.source_uri,
            source_label=c.source_label,
            index=idx,
            score=c.score,
            chunk_index=c.chunk_index,
            preview=c.preview,
        )
        for idx, c in enumerate(unique, start=1)
    ]
