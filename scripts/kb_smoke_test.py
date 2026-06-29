#!/usr/bin/env python3
"""Live Bedrock KB smoke test — calls BedrockRagClient.ask() against real AWS."""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.bedrock_client import BedrockRagClient  # noqa: E402
from app.config import Config  # noqa: E402
from app.errors import BedrockError  # noqa: E402


def _load_questions() -> list[dict]:
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


def run_smoke() -> tuple[int, int, list[dict], str]:
    cfg = Config.from_env()
    client = BedrockRagClient(cfg)
    model_arn = cfg.BEDROCK_MODEL_ARN
    questions = _load_questions()
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
                    "grounded": None,
                    "citations": 0,
                    "citation_labels": [],
                    "status": "PASS" if ok else "FAIL",
                    "failures": failures,
                    "answer_preview": "",
                    "answer_text": "",
                },
            )
            print(f"[{'PASS' if ok else 'FAIL'}] #{qid}: {question[:60]}...")
            continue

        expect_grounded = item["expect_grounded"]

        try:
            result = client.ask(question)
        except BedrockError as exc:
            failures.append(f"Bedrock error: {exc.user_message}")
            rows.append(
                {
                    "id": qid,
                    "question": question,
                    "grounded": None,
                    "citations": 0,
                    "citation_labels": [],
                    "status": "FAIL",
                    "failures": failures,
                    "answer_preview": "",
                    "answer_text": "",
                },
            )
            print(f"[FAIL] #{qid}: {question[:60]}... ({exc.user_message})")
            continue

        if result.grounded != expect_grounded:
            failures.append(
                f"grounded={result.grounded}, expected={expect_grounded}",
            )

        if expect_grounded:
            if not result.citations:
                failures.append("expected citations when grounded")
            expected_sources = item.get("expected_source_contains", [])
            if expected_sources and not _source_hit(result.citations, expected_sources):
                failures.append(
                    f"citations missing expected source fragment(s): {expected_sources}",
                )
            keywords = item.get("answer_keywords", [])
            if keywords and not _keyword_hit(result.answer, keywords):
                failures.append(f"answer missing keywords: {keywords}")
        else:
            forbidden = item.get("forbidden_answer_keywords", [])
            if _keyword_hit(result.answer, forbidden):
                failures.append(f"answer contained forbidden keywords: {forbidden}")

        ok = not failures
        if ok:
            passed += 1

        citation_labels = [c.source_label for c in result.citations]
        rows.append(
            {
                "id": qid,
                "question": question,
                "grounded": result.grounded,
                "citations": len(result.citations),
                "citation_labels": citation_labels,
                "status": "PASS" if ok else "FAIL",
                "failures": failures,
                "answer_preview": result.answer[:240].replace("\n", " "),
                "answer_text": result.answer.strip(),
            },
        )
        print(f"[{'PASS' if ok else 'FAIL'}] #{qid}: {question[:60]}...")

    return passed, len(questions), rows, model_arn


def write_results(passed: int, total: int, rows: list[dict], model_arn: str = "") -> Path:
    out = ROOT / "evaluation" / "smoke_results.md"
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Bedrock KB Smoke Test Results",
        "",
        f"- **Run at:** {ts}",
        f"- **Model:** `{model_arn}`" if model_arn else "- **Model:** (not recorded)",
        f"- **Score:** {passed}/{total} PASS",
        "",
        "| # | Question | Grounded | Citations | Status |",
        "|---|----------|----------|-----------|--------|",
    ]
    for row in rows:
        q = row["question"].replace("|", "\\|")[:70]
        lines.append(
            f"| {row['id']} | {q} | {row['grounded']} | {row['citations']} | **{row['status']}** |",
        )
    lines.extend(["", "## Details", ""])
    for row in rows:
        lines.append(f"### {row['id']}. {row['question']}")
        lines.append(f"- Status: **{row['status']}**")
        lines.append(f"- Grounded: `{row['grounded']}` · Citations: `{row['citations']}`")
        if row["failures"]:
            for f in row["failures"]:
                lines.append(f"- Failure: {f}")
        lines.append(f"- Answer preview: {row['answer_preview']}")
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


SHOWCASE_IDS = (1, 2, 3, 4, 5)


def write_qa_showcase(rows: list[dict], model_arn: str = "") -> Path:
    """Submission artifact: grounded Q&A + off-corpus refusal (screenshot 19)."""
    out = ROOT / "evaluation" / "qa_showcase.md"
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    s3_prefix = "s3://<bucket-name>/projects/piter-aiops/knowledge_base/"
    lines = [
        "# Sample Questions and Answers — Live Bedrock KB",
        "",
        f"- **Run at:** {ts}",
        f"- **Model:** `{model_arn}`" if model_arn else "- **Model:** (not recorded)",
        f"- **Corpus:** {s3_prefix}",
        "- **Cases:** 4 grounded runbook answers + 1 off-topic refusal",
        "",
    ]
    for row in rows:
        if row["id"] not in SHOWCASE_IDS or row["status"] != "PASS":
            continue
        q = row["question"].replace("|", "\\|")
        lines.append(f"## {row['id']}. {q}")
        lines.append("")
        lines.append(f"- **Grounded:** `{row['grounded']}` · **Citations:** {row['citations']}")
        labels = row.get("citation_labels") or []
        if labels:
            lines.append(f"- **Sources:** {', '.join(f'`{label}`' for label in labels)}")
        lines.append("")
        answer = (row.get("answer_text") or row["answer_preview"] or "").strip()
        if len(answer) > 720:
            answer = answer[:720].rstrip() + "…"
        lines.append("**Answer:**")
        lines.append("")
        for paragraph in answer.split("\n"):
            paragraph = paragraph.strip()
            if paragraph:
                lines.append(paragraph)
                lines.append("")
        lines.append("---")
        lines.append("")

    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out


def main() -> int:
    passed, total, rows, model_arn = run_smoke()
    out = write_results(passed, total, rows, model_arn)
    showcase = write_qa_showcase(rows, model_arn)
    print(f"\n{passed}/{total} passed — wrote {out}")
    print(f"Showcase: {showcase}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
