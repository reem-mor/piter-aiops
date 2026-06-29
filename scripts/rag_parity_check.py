#!/usr/bin/env python3
"""Semantic parity check: Bedrock Agent vs local TF-IDF KB on demo_questions.json."""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.bedrock_agent_client import BedrockAgentClient  # noqa: E402
from app.config import Config  # noqa: E402
from app.errors import BedrockError  # noqa: E402
from app.local_agent import LocalRagClient  # noqa: E402
from app.text_utils import _PITER_SECTION_HEADINGS  # noqa: E402

EVAL_PATH = ROOT / "evaluation" / "demo_questions.json"
OUT_PATH = ROOT / "evaluation" / "rag_parity_results.md"


def _load_questions() -> list[dict]:
    return json.loads(EVAL_PATH.read_text(encoding="utf-8"))


def _keyword_hit(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return all(kw.lower() in lower for kw in keywords)


def _missing_keywords(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [kw for kw in keywords if kw.lower() not in lower]


def _normalize_stem(label: str) -> str:
    name = label.rsplit("/", 1)[-1]
    for suffix in (".json", ".md"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name.lower().replace("-", "_")


def _source_hit(citations: list, fragments: list[str]) -> bool:
    if not fragments:
        return True
    uris = " ".join((c.source_uri or "") for c in citations).lower()
    labels = " ".join(getattr(c, "source_label", "") for c in citations).lower()
    snippets = " ".join(c.snippet for c in citations).lower()
    stems = " ".join(_normalize_stem(getattr(c, "source_label", "") or "") for c in citations)
    blob = f"{uris} {labels} {snippets} {stems}"
    return any(frag.lower().replace("-", "_") in blob for frag in fragments)


def _missing_sources(citations: list, fragments: list[str]) -> list[str]:
    if not fragments:
        return []
    uris = " ".join((c.source_uri or "") for c in citations).lower()
    labels = " ".join(getattr(c, "source_label", "") for c in citations).lower()
    snippets = " ".join(c.snippet for c in citations).lower()
    stems = " ".join(_normalize_stem(getattr(c, "source_label", "") or "") for c in citations)
    blob = f"{uris} {labels} {snippets} {stems}"
    return [
        frag
        for frag in fragments
        if frag.lower().replace("-", "_") not in blob
    ]


def _piter_sections_present(text: str) -> list[str]:
    found: list[str] = []
    for name, pattern in _PITER_SECTION_HEADINGS.items():
        if pattern.search(text):
            found.append(name)
    return found


def _classify_failure(
    *,
    grounded_match: bool,
    agent_grounded: bool | None,
    local_grounded: bool | None,
    source_match: bool,
    agent_sources_ok: bool,
    local_sources_ok: bool,
    keywords_match: bool,
    agent_kw_ok: bool,
    local_kw_ok: bool,
) -> str:
    if not grounded_match:
        return "corpus_or_retrieval"
    if not source_match:
        if agent_sources_ok != local_sources_ok:
            return "retrieval_mismatch"
        return "retrieval_mismatch"
    if not keywords_match:
        if not local_kw_ok and agent_kw_ok:
            return "local_compose_answer"
        if not agent_kw_ok and local_kw_ok:
            return "agent_variance"
        return "eval_keywords_strict"
    return "ok"


def _evaluate_side(
    result,
    *,
    expect_grounded: bool | None,
    source_frags: list[str],
    keywords: list[str],
    check_sections: bool,
) -> dict:
    failures: list[str] = []
    if expect_grounded is True and not result.grounded:
        failures.append("expected grounded but got no citations")
    if expect_grounded is False and result.grounded:
        failures.append("expected refusal but got citations")
    missing_src = _missing_sources(result.citations, source_frags) if expect_grounded else []
    if missing_src:
        failures.append(f"citations missing sources: {missing_src}")
    missing_kw = _missing_keywords(result.answer, keywords) if keywords else []
    if missing_kw:
        failures.append(f"answer missing keywords: {missing_kw}")
    sections = _piter_sections_present(result.answer) if check_sections else []
    if check_sections and len(sections) < 4:
        failures.append(f"missing PITER sections (found: {sections})")
    return {
        "grounded": result.grounded,
        "matched_runbook": result.matched_runbook,
        "citation_labels": [c.source_label for c in result.citations],
        "latency_ms": result.latency_ms,
        "mode": result.mode,
        "answer_preview": result.answer[:300],
        "failures": failures,
        "sources_ok": not missing_src,
        "keywords_ok": not missing_kw,
        "sections": sections,
    }


def run_parity() -> tuple[int, int, list[dict], str]:
    cfg = Config.from_env()
    agent = BedrockAgentClient(cfg)
    local = LocalRagClient(Config.local())
    agent_ref = f"{cfg.BEDROCK_AGENT_ID}/{cfg.BEDROCK_AGENT_ALIAS_ID}"
    rows: list[dict] = []
    passed = 0

    for item in _load_questions():
        qid = item["id"]
        question = item["question"]
        row: dict = {"id": qid, "question": question}

        if item.get("expect_validation_error"):
            agent_err = local_err = None
            try:
                agent.ask(question)
                agent_err = "expected validation error but ask() succeeded"
            except BedrockError as exc:
                if item.get("expected_reason") and exc.code != item["expected_reason"]:
                    agent_err = f"reason={exc.code}, expected={item['expected_reason']}"
            try:
                local.ask(question)
                local_err = "expected validation error but ask() succeeded"
            except BedrockError as exc:
                if item.get("expected_reason") and exc.code != item["expected_reason"]:
                    local_err = f"reason={exc.code}, expected={item['expected_reason']}"
            ok = not agent_err and not local_err
            row.update(
                {
                    "status": "PASS" if ok else "FAIL",
                    "validation": True,
                    "agent_error": agent_err,
                    "local_error": local_err,
                    "root_cause": "ok" if ok else "validation",
                }
            )
            if ok:
                passed += 1
            rows.append(row)
            continue

        expect_grounded = item.get("expect_grounded")
        source_frags = item.get("expected_source_contains") or []
        keywords = item.get("answer_keywords") or []
        check_sections = qid == 2

        try:
            agent_result = agent.ask(question)
        except BedrockError as exc:
            row.update(
                {
                    "status": "FAIL",
                    "agent": {"error": f"{exc.code}: {exc.user_message}"},
                    "local": {},
                    "root_cause": "agent_bedrock_error",
                }
            )
            rows.append(row)
            continue

        local_result = local.ask(question)
        agent_eval = _evaluate_side(
            agent_result,
            expect_grounded=expect_grounded,
            source_frags=source_frags,
            keywords=keywords,
            check_sections=check_sections,
        )
        local_eval = _evaluate_side(
            local_result,
            expect_grounded=expect_grounded,
            source_frags=source_frags,
            keywords=keywords,
            check_sections=check_sections,
        )

        grounded_match = agent_eval["grounded"] == local_eval["grounded"]
        source_match = agent_eval["sources_ok"] and local_eval["sources_ok"]
        keywords_match = agent_eval["keywords_ok"] and local_eval["keywords_ok"]
        semantic_ok = grounded_match and source_match and keywords_match

        parity_failures: list[str] = []
        if not grounded_match:
            parity_failures.append(
                f"grounded mismatch: agent={agent_eval['grounded']}, local={local_eval['grounded']}"
            )
        if not source_match:
            parity_failures.append("expected source fragments not found on both sides")
        if not keywords_match:
            parity_failures.append("answer_keywords not satisfied on both sides")

        root_cause = _classify_failure(
            grounded_match=grounded_match,
            agent_grounded=agent_eval["grounded"],
            local_grounded=local_eval["grounded"],
            source_match=source_match,
            agent_sources_ok=agent_eval["sources_ok"],
            local_sources_ok=local_eval["sources_ok"],
            keywords_match=keywords_match,
            agent_kw_ok=agent_eval["keywords_ok"],
            local_kw_ok=local_eval["keywords_ok"],
        )

        # Retrieval-only layer for diagnosis
        local_retrieval = [c.document for c in local.retrieve(question)]

        row.update(
            {
                "status": "PASS" if semantic_ok else "FAIL",
                "agent": agent_eval,
                "local": local_eval,
                "local_retrieval_top": local_retrieval[:5],
                "parity_failures": parity_failures,
                "root_cause": root_cause,
            }
        )
        if semantic_ok:
            passed += 1
        rows.append(row)

    return passed, len(rows), rows, agent_ref


def write_results(passed: int, total: int, rows: list[dict], agent_ref: str) -> Path:
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# RAG Parity Results (Bedrock Agent vs Local KB)",
        "",
        f"- **Run at:** {ts}",
        f"- **Agent ref:** `{agent_ref}`",
        f"- **Score:** {passed}/{total} semantic PASS",
        "",
        "Parity criteria: same `grounded` decision, `expected_source_contains` on both sides, "
        "`answer_keywords` on both sides. Answer text may differ.",
        "",
        "| ID | Status | Agent grounded | Local grounded | Root cause |",
        "|----|--------|----------------|----------------|------------|",
    ]
    for row in rows:
        if row.get("validation"):
            status = row["status"]
            lines.append(f"| {row['id']} | {status} | validation | validation | {row.get('root_cause', '')} |")
            continue
        agent_g = row.get("agent", {}).get("grounded", "—")
        local_g = row.get("local", {}).get("grounded", "—")
        lines.append(
            f"| {row['id']} | {row['status']} | {agent_g} | {local_g} | {row.get('root_cause', '')} |"
        )

    lines.append("")
    for row in rows:
        lines.append(f"## Question {row['id']}")
        lines.append("")
        lines.append(f"**Q:** {row['question']}")
        lines.append(f"**Status:** {row['status']}")
        if row.get("validation"):
            lines.append(f"- Agent validation: {row.get('agent_error') or 'OK'}")
            lines.append(f"- Local validation: {row.get('local_error') or 'OK'}")
            lines.append("")
            continue
        if row.get("parity_failures"):
            lines.append("**Parity failures:**")
            for f in row["parity_failures"]:
                lines.append(f"- {f}")
        lines.append("")
        lines.append("### Agent")
        agent = row.get("agent", {})
        if agent.get("error"):
            lines.append(f"- Error: {agent['error']}")
        else:
            lines.append(f"- Grounded: {agent.get('grounded')}")
            lines.append(f"- Matched: {agent.get('matched_runbook')}")
            lines.append(f"- Citations: {agent.get('citation_labels', [])}")
            if agent.get("failures"):
                lines.append(f"- Side failures: {agent['failures']}")
            lines.append(f"- Preview: {agent.get('answer_preview', '')[:200]}...")
        lines.append("")
        lines.append("### Local")
        local = row.get("local", {})
        lines.append(f"- Grounded: {local.get('grounded')}")
        lines.append(f"- Matched: {local.get('matched_runbook')}")
        lines.append(f"- Citations: {local.get('citation_labels', [])}")
        lines.append(f"- Retrieval top: {row.get('local_retrieval_top', [])}")
        if local.get("failures"):
            lines.append(f"- Side failures: {local['failures']}")
        lines.append(f"- Preview: {local.get('answer_preview', '')[:200]}...")
        lines.append("")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return OUT_PATH


def main() -> int:
    passed, total, rows, agent_ref = run_parity()
    out = write_results(passed, total, rows, agent_ref)
    print(f"\n{passed}/{total} semantic parity PASS — wrote {out}")
    for row in rows:
        if row["status"] == "FAIL":
            print(f"  FAIL #{row['id']}: {row.get('root_cause')} — {row.get('parity_failures', row.get('agent', {}))}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
