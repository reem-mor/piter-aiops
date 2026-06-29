#!/usr/bin/env python3
"""Live Bedrock Agent smoke test — calls get_rag_client().ask() against real AWS."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Config  # noqa: E402
from app.errors import BedrockError  # noqa: E402
from app.rag_factory import get_rag_client  # noqa: E402

OPS_QUESTIONS = [
    {
        "id": "ops-1",
        "question": "What's the current status of GIB?",
        "answer_keywords": ["DEGRADED", "degraded", "GIB"],
    },
    {
        "id": "ops-2",
        "question": "Show me alerts in GIB from the last 6 hours.",
        "answer_keywords": ["GIB", "alert"],
    },
    {
        "id": "ops-3",
        "question": "Are there any active alerts in MGM right now?",
        "answer_keywords": ["MGM"],
    },
]


def _load_questions(*, ops_only: bool) -> list[dict]:
    if ops_only:
        return OPS_QUESTIONS
    path = ROOT / "evaluation" / "demo_questions.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _keyword_hit(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords)


def _source_hit(citations: list, fragments: list[str]) -> bool:
    uris = " ".join((c.source_uri or "") for c in citations).lower()
    labels = " ".join(getattr(c, "source_label", "") for c in citations).lower()
    snippets = " ".join(c.snippet for c in citations).lower()
    blob = f"{uris} {labels} {snippets}"
    return any(frag.lower() in blob for frag in fragments)


def run_smoke(*, ops_only: bool = False) -> tuple[int, int, list[dict], str]:
    cfg = Config.from_env()
    client = get_rag_client(cfg)
    backend = cfg.RAG_BACKEND
    agent_ref = f"{cfg.BEDROCK_AGENT_ID}/{cfg.BEDROCK_AGENT_ALIAS_ID}" if backend == "agent" else cfg.BEDROCK_MODEL_ARN
    questions = _load_questions(ops_only=ops_only)
    rows: list[dict] = []
    passed = 0

    for item in questions:
        qid = item["id"]
        question = item["question"]
        failures: list[str] = []

        if item.get("expect_validation_error"):
            try:
                client.ask(question)
                failures.append("expected validation error but ask() succeeded")
            except BedrockError as exc:
                expected = item.get("expected_reason")
                if expected and exc.code != expected:
                    failures.append(f"reason={exc.code}, expected={expected}")
            ok = not failures
            if ok:
                passed += 1
            rows.append(
                {
                    "id": qid,
                    "question": question,
                    "status": "PASS" if ok else "FAIL",
                    "failures": failures,
                    "backend": backend,
                },
            )
            continue

        try:
            result = client.ask(question)
        except BedrockError as exc:
            failures.append(f"BedrockError: {exc.user_message} ({exc.code})")
            rows.append(
                {
                    "id": qid,
                    "question": question,
                    "status": "FAIL",
                    "failures": failures,
                    "backend": backend,
                },
            )
            continue

        expect_grounded = item.get("expect_grounded")
        if expect_grounded is True and not result.grounded:
            failures.append("expected grounded answer but got no citations")
        if expect_grounded is False and result.grounded:
            failures.append("expected refusal/low confidence but got citations")

        keywords = item.get("answer_keywords") or []
        if keywords and not _keyword_hit(result.answer, keywords):
            failures.append(f"answer missing keywords: {keywords}")

        source_frags = item.get("source_fragments") or []
        if source_frags and expect_grounded is True and not _source_hit(result.citations, source_frags):
            failures.append(f"citations missing source fragments: {source_frags}")

        ok = not failures
        if ok:
            passed += 1

        rows.append(
            {
                "id": qid,
                "question": question,
                "status": "PASS" if ok else "FAIL",
                "failures": failures,
                "grounded": result.grounded,
                "citations": len(result.citations),
                "citation_labels": [c.source_label for c in result.citations],
                "latency_ms": result.latency_ms,
                "answer_preview": result.answer[:200],
                "answer_text": result.answer,
                "backend": backend,
            },
        )

    return passed, len(questions), rows, agent_ref


def write_results(
    passed: int,
    total: int,
    rows: list[dict],
    agent_ref: str,
    *,
    ops_only: bool,
) -> Path:
    out_name = "agent_ops_smoke_results.md" if ops_only else "agent_smoke_results.md"
    out = ROOT / "evaluation" / out_name
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    title = "Bedrock Agent Ops Smoke Test Results" if ops_only else "Bedrock Agent Smoke Test Results"
    lines = [
        f"# {title}",
        "",
        f"- **Run at:** {ts}",
        f"- **Backend / ref:** `{agent_ref}`",
        f"- **Score:** {passed}/{total} PASS",
        "",
        "| ID | Status | Grounded | Citations | Latency ms |",
        "|----|--------|----------|-----------|------------|",
    ]
    for row in rows:
        if row.get("expect_validation_error"):
            continue
        lines.append(
            f"| {row['id']} | {row['status']} | "
            f"{row.get('grounded', '—')} | {row.get('citations', '—')} | "
            f"{row.get('latency_ms', '—')} |",
        )
    lines.append("")
    for row in rows:
        if row["status"] == "FAIL":
            lines.append(f"### FAIL #{row['id']}: {row['question']}")
            for f in row.get("failures", []):
                lines.append(f"- {f}")
            lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Live Bedrock Agent smoke test")
    parser.add_argument(
        "--ops",
        action="store_true",
        help="Run ops action-group prompts only (GIB status/alerts)",
    )
    args = parser.parse_args()

    passed, total, rows, agent_ref = run_smoke(ops_only=args.ops)
    out = write_results(passed, total, rows, agent_ref, ops_only=args.ops)
    print(f"\n{passed}/{total} passed — wrote {out}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
