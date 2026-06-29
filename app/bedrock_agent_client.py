"""boto3 wrapper for Amazon Bedrock Agents invoke_agent (KB-backed)."""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import EventStreamError

from app.bedrock_client import BedrockRagClient, Citation, RagAnswer, _dedupe_citations
from app.config import Config
from app.errors import translate
from app.text_utils import extract_reference_metadata, format_citation_label, format_citation_preview
from app.validators import validate_question

log = logging.getLogger(__name__)

# Deployed agent instructions live in infra/bedrock_agent_instructions.txt (AWS console).
# This constant is documentation-only; invoke_agent does not send it at runtime.
AGENT_INSTRUCTION = """You are PITER Ops, an enterprise Site Reliability Engineering assistant for regulated betting platforms.

Mandatory workflow (always in this order):
1. Priority — classify P1–P4 using severity policy and business impact evidence.
2. Investigation — use knowledge-base citations and tool results only; never invent facts.
3. Triage — ordered, reversible steps first; cite the runbook for each step.
4. Escalation — when P1–P3 or regulatory exposure; name the on-call path from policy.
5. Resolution — validation checks and post-incident follow-up.

Grounding rules:
- Every remediation step must cite a runbook, policy, or incident record from retrieval.
- If evidence is missing, state "Not in knowledge base" and recommend what data to collect.
- Never invent service owners, deploy versions, contacts, escalation paths, or past incidents.

Safety rules (non-negotiable):
- REFUSE to provide executable steps for: FLUSHALL/FLUSHDB, DROP/TRUNCATE, mass DELETE,
  unapproved failover/replica promotion, disabling WAF/MFA/auth, firewall widening, or
  "scale to zero" / kill-all-sessions without scoped approval.
- For those topics, explain risk, cite the runbook's "Dangerous actions" section, and
  direct the operator to human approval and change control.
- Never recommend auto-executing production changes without explicit human sign-off.
- Never help bypass notification allowlists, confirmation tokens, or audit requirements.

Output format (concise, scannable for on-call):

Priority:
Investigation findings:
Triage plan:
Escalation recommendation:
Resolution plan:
Business impact:
Sources:
Confidence and uncertainty:
"""


def build_session_attributes(
    *,
    alert_id: str | None = None,
    service: str | None = None,
    environment: str | None = None,
    severity: str | None = None,
    symptom: str | None = None,
    alert_time: str | None = None,
    triage_complete: str = "false",
) -> tuple[dict[str, str], dict[str, str]]:
    """Session + prompt attributes for multi-turn triage memory."""
    session: dict[str, str] = {}
    prompt: dict[str, str] = {}
    if alert_id:
        session["alert_id"] = alert_id
    if service:
        session["service"] = service
        prompt["current_service"] = service
    if environment:
        session["environment"] = environment
        prompt["current_environment"] = environment
    if severity:
        session["severity"] = severity
    if symptom:
        session["symptom"] = symptom
    if alert_time:
        session["alert_time"] = alert_time
    session["triage_complete"] = triage_complete
    if triage_complete == "true":
        prompt["follow_up_mode"] = (
            "Prior triage is complete. Answer follow-up questions using session context; "
            "do not repeat full triage unless the user asks to re-run."
        )
    return session, prompt


class BedrockAgentClient:
    """Question in via invoke_agent; grounded answer + citations + enrichment out."""

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

    def ask(
        self,
        question: str,
        *,
        session_id: str | None = None,
        session_attributes: dict[str, str] | None = None,
        prompt_session_attributes: dict[str, str] | None = None,
    ) -> RagAnswer:
        question = validate_question(question)
        started = time.perf_counter()
        request: dict[str, Any] = {
            "agentId": self._config.BEDROCK_AGENT_ID,
            "agentAliasId": self._config.BEDROCK_AGENT_ALIAS_ID,
            "inputText": question,
            "sessionId": session_id or str(uuid.uuid4()),
            "enableTrace": True,
        }
        if session_attributes:
            request["sessionState"] = request.get("sessionState", {})
            request["sessionState"]["sessionAttributes"] = session_attributes
        if prompt_session_attributes:
            request["sessionState"] = request.get("sessionState", {})
            request["sessionState"]["promptSessionAttributes"] = prompt_session_attributes

        try:
            response = self._client.invoke_agent(**request)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "Bedrock invoke_agent failed agent=%s alias=%s: %s",
                self._config.BEDROCK_AGENT_ID,
                self._config.BEDROCK_AGENT_ALIAS_ID,
                exc,
            )
            raise translate(exc) from exc

        log.info(
            "Bedrock invoke_agent started agent=%s alias=%s session=%s",
            self._config.BEDROCK_AGENT_ID,
            self._config.BEDROCK_AGENT_ALIAS_ID,
            request.get("sessionId"),
        )

        answer_parts: list[str] = []
        citations_raw: list[dict[str, Any]] = []
        enrichment: dict[str, Any] = {}
        out_session_id = response.get("sessionId")

        try:
            for event in response.get("completion", []):
                chunk = event.get("chunk")
                if chunk:
                    raw_bytes = chunk.get("bytes")
                    if raw_bytes:
                        answer_parts.append(raw_bytes.decode("utf-8"))
                    attribution = chunk.get("attribution") or {}
                    for citation in attribution.get("citations", []) or []:
                        for ref in citation.get("retrievedReferences", []) or []:
                            citations_raw.append(ref)

                trace = event.get("trace") or {}
                inner = trace.get("trace") or trace
                orch = inner.get("orchestrationTrace")
                if not orch:
                    continue
                observation = orch.get("observation") or {}
                kb_out = observation.get("knowledgeBaseLookupOutput") or {}
                for ref in kb_out.get("retrievedReferences", []) or []:
                    citations_raw.append(ref)
                action_out = observation.get("actionGroupInvocationOutput") or {}
                if action_out:
                    _merge_action_output(enrichment, action_out)
        except EventStreamError as exc:
            log.warning("Bedrock invoke_agent stream failed: %s", exc)
            raise translate(exc) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        answer_text = "".join(answer_parts).strip()
        citations = _parse_references(citations_raw)
        grounded = bool(citations)
        log.info(
            "Bedrock invoke_agent completed session=%s latency_ms=%d grounded=%s citations=%d",
            out_session_id,
            latency_ms,
            grounded,
            len(citations),
        )
        if not grounded and not answer_text:
            answer_text = "I could not find anything in the knowledge base for that question."

        if not grounded:
            return self._backfill_from_kb(
                question,
                session_id=out_session_id,
                agent_answer=answer_text,
                enrichment=enrichment,
                latency_ms=latency_ms,
            )

        matched = citations[0].source_label if citations else None
        return RagAnswer(
            answer=answer_text,
            citations=citations,
            session_id=out_session_id,
            grounded=grounded,
            latency_ms=latency_ms,
            matched_runbook=matched,
            enrichment=enrichment or None,
            mode="bedrock_agent",
        )

    def _backfill_from_kb(
        self,
        question: str,
        *,
        session_id: str | None,
        agent_answer: str,
        enrichment: dict[str, Any],
        latency_ms: int,
    ) -> RagAnswer:
        """When invoke_agent skips KB retrieval, use direct RetrieveAndGenerate."""
        rag = BedrockRagClient(self._config, client=self._client).ask(question)
        if rag.grounded:
            log.info(
                "Agent answer was ungrounded; backfilled citations via retrieve_and_generate (%d sources)",
                len(rag.citations),
            )
            return RagAnswer(
                answer=rag.answer,
                citations=rag.citations,
                session_id=session_id,
                grounded=True,
                latency_ms=latency_ms + rag.latency_ms,
                matched_runbook=rag.matched_runbook,
                enrichment=enrichment or None,
                mode="bedrock_agent",
            )

        return RagAnswer(
            answer=agent_answer or rag.answer,
            citations=[],
            session_id=session_id,
            grounded=False,
            latency_ms=latency_ms + rag.latency_ms,
            matched_runbook=None,
            enrichment=enrichment or None,
            mode="bedrock_agent",
        )


def _merge_action_output(enrichment: dict[str, Any], action_out: dict[str, Any]) -> None:
    text = action_out.get("text") or ""
    if not text:
        return
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        enrichment.setdefault("raw_tool_outputs", []).append(text)
        return
    if isinstance(body, dict):
        for key in (
            "deployments",
            "owner_team",
            "similar_incidents",
            "revenue_impact_usd_per_hour",
            "likely_deploy_correlation",
        ):
            if key in body:
                enrichment[key] = body[key]
        if "error" not in body:
            enrichment.setdefault("tools", []).append(body)


def _parse_references(refs: list[dict[str, Any]]) -> list[Citation]:
    parsed: list[Citation] = []
    for ref in refs:
        snippet = (ref.get("content", {}) or {}).get("text", "").strip()
        if not snippet:
            continue
        location = ref.get("location", {}) or {}
        source_uri = (location.get("s3Location", {}) or {}).get("uri")
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
    return _dedupe_citations(parsed)
