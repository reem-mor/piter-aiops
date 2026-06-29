"""Small text helpers for workflow UI and citation formatting."""
from __future__ import annotations

import json
import re
from typing import Any


def format_citation_label(source_uri: str | None) -> str:
    """Human-readable document name from any S3 or file URI."""
    if not source_uri:
        return "Unknown source"
    path = source_uri.split("://", 1)[-1]
    name = path.rsplit("/", 1)[-1]
    return name or "Unknown source"


def parse_action_bullets(answer: str, *, limit: int = 8) -> list[str]:
    """Heuristic: pull list-like lines from a free-text model answer."""
    bullets: list[str] = []
    for line in answer.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^[-*•]\s+(.+)$", stripped)
        if match:
            bullets.append(match.group(1).strip())
            continue
        match = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if match:
            bullets.append(match.group(1).strip())
    if bullets:
        return bullets[:limit]
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", answer) if len(s.strip()) > 20]
    return sentences[: min(limit, 4)]


_SECTION_HEADINGS = {
    "summary": re.compile(r"^(summary|overview)\s*:?\s*$", re.I),
    "steps": re.compile(r"^(recommended\s+steps?|steps?|actions?)\s*:?\s*$", re.I),
    "escalation": re.compile(r"^escalation\s*:?\s*$", re.I),
    "why": re.compile(r"^(why\s+this\s+answer|why|sources?)\s*:?\s*$", re.I),
}

_PITER_SECTION_HEADINGS = {
    "priority": re.compile(r"^priority\s*:?\s*$", re.I),
    "investigation": re.compile(r"^investigation(\s+findings?)?\s*:?\s*$", re.I),
    "triage": re.compile(r"^triage(\s+plan)?\s*:?\s*$", re.I),
    "escalation_rec": re.compile(r"^escalation(\s+recommendation)?\s*:?\s*$", re.I),
    "resolution": re.compile(r"^resolution(\s+plan)?\s*:?\s*$", re.I),
    "business_impact": re.compile(r"^business\s+impact\s*:?\s*$", re.I),
    "sources": re.compile(r"^sources?\s*:?\s*$", re.I),
    "confidence": re.compile(r"^confidence(\s+and\s+uncertainty)?\s*:?\s*$", re.I),
}

_INLINE_WHY = re.compile(r"\bwhy\s+this\s+answer\s*:\s*", re.I)
_INLINE_ESCALATION = re.compile(r"\bescalation\s*:\s*", re.I)
_NUMBERED_SPLIT = re.compile(r"(?<=\s)(?=\d+\.\s)")


def _split_inline_numbered_steps(text: str) -> list[str]:
    """Split '1. foo 2. bar' on one line into separate step strings."""
    text = text.strip()
    if not text:
        return []
    if not re.search(r"\d+\.\s", text):
        return [text]
    parts = _NUMBERED_SPLIT.split(text)
    steps: list[str] = []
    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue
        match = re.match(r"^\d+[.)]\s+(.+)$", stripped, re.S)
        steps.append(match.group(1).strip() if match else stripped)
    return steps


def _split_bullets(text: str) -> list[str]:
    items: list[str] = []
    for chunk in re.split(r"(?<=[.!?])\s+(?=[-•*]\s+)|\n+", text):
        stripped = chunk.strip()
        if not stripped:
            continue
        bullet = re.match(r"^[-*•]\s+(.+)$", stripped)
        items.append(bullet.group(1).strip() if bullet else stripped)
    return items


def _split_step_payload(text: str) -> tuple[list[str], list[str], str]:
    """Extract inline steps, escalation bullets, and why text from one blob."""
    blob = text.strip()
    why = ""
    escalation: list[str] = []

    why_parts = _INLINE_WHY.split(blob, maxsplit=1)
    if len(why_parts) == 2:
        blob, why = why_parts[0].strip(), why_parts[1].strip()

    esc_parts = _INLINE_ESCALATION.split(blob, maxsplit=1)
    if len(esc_parts) == 2:
        blob, esc_rest = esc_parts[0].strip(), esc_parts[1].strip()
        if esc_rest:
            escalation.extend(_split_bullets(esc_rest) or [esc_rest])

    steps = _split_inline_numbered_steps(blob)
    if not steps and blob:
        steps = [blob]
    return steps, escalation, why


def _normalize_step_buckets(
    steps: list[str],
    escalation: list[str],
    why_parts: list[str],
) -> tuple[list[str], list[str], str]:
    """Flatten jammed step lines and route inline Escalation/Why markers."""
    flat_steps: list[str] = []
    flat_escalation = list(escalation)
    flat_why = " ".join(why_parts).strip()

    for step in steps:
        sub_steps, sub_esc, sub_why = _split_step_payload(step)
        flat_steps.extend(sub_steps)
        flat_escalation.extend(sub_esc)
        if sub_why and not flat_why:
            flat_why = sub_why

    return flat_steps, flat_escalation, flat_why


def _join_bucket(parts: list[str]) -> str:
    return " ".join(parts).strip()


def _parse_piter_sections(text: str) -> dict[str, Any] | None:
    """Parse PITER-structured answers; returns None if no PITER headings found."""
    lines = text.splitlines()
    buckets: dict[str, list[str]] = {key: [] for key in _PITER_SECTION_HEADINGS}
    current: str | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        matched_key = None
        for key, pattern in _PITER_SECTION_HEADINGS.items():
            if pattern.match(stripped):
                matched_key = key
                rest = pattern.sub("", stripped).strip()
                if rest:
                    buckets[key].append(rest)
                break
        if matched_key:
            current = matched_key
            continue

        bullet = re.match(r"^[-*•]\s+(.+)$", stripped)
        numbered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if current == "triage" and numbered:
            buckets["triage"].append(numbered.group(1).strip())
        elif current == "escalation_rec" and (bullet or numbered):
            buckets["escalation_rec"].append(
                (bullet or numbered).group(1).strip(),  # type: ignore[union-attr]
            )
        elif current == "triage" and bullet:
            buckets["triage"].append(bullet.group(1).strip())
        elif current == "escalation_rec" and bullet:
            buckets["escalation_rec"].append(bullet.group(1).strip())
        elif current:
            buckets[current].append(stripped)

    if not any(buckets.values()):
        return None

    # Legacy answers use Summary/Recommended steps — not PITER unless priority or
    # investigation+triage pillars are present (avoids matching "Escalation:" alone).
    if not buckets["priority"] and not (
        buckets["investigation"] and buckets["triage"]
    ):
        return None

    triage_steps, escalation_items, _ = _normalize_step_buckets(
        buckets["triage"],
        buckets["escalation_rec"],
        [],
    )
    if not triage_steps:
        triage_steps = parse_action_bullets(_join_bucket(buckets["triage"]))

    piter = {
        "priority": _join_bucket(buckets["priority"]),
        "investigation": _join_bucket(buckets["investigation"]),
        "triage_plan": triage_steps,
        "escalation": escalation_items or _split_bullets(_join_bucket(buckets["escalation_rec"])),
        "resolution": _join_bucket(buckets["resolution"]),
        "business_impact": _join_bucket(buckets["business_impact"]),
        "sources": _join_bucket(buckets["sources"]),
        "confidence": _join_bucket(buckets["confidence"]),
    }
    summary_parts = [piter["priority"], piter["investigation"]]
    summary = " ".join(p for p in summary_parts if p).strip()
    why_parts = [piter["sources"], piter["confidence"]]
    why = " ".join(p for p in why_parts if p).strip()
    return {
        "summary": summary,
        "steps": triage_steps,
        "escalation": piter["escalation"],
        "why": why or "Based on retrieved runbook, alert history, or postmortem in the Knowledge Base.",
        "piter_sections": piter,
    }


def format_answer_sections(raw: str) -> dict[str, Any]:
    """Parse structured answer sections or derive them from free text."""
    text = (raw or "").strip()
    if not text:
        return {"summary": "", "steps": [], "escalation": [], "why": ""}

    piter_parsed = _parse_piter_sections(text)
    if piter_parsed is not None:
        return piter_parsed

    lines = text.splitlines()
    buckets: dict[str, list[str]] = {
        "summary": [],
        "steps": [],
        "escalation": [],
        "why": [],
    }
    current = "summary"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        matched_key = None
        for key, pattern in _SECTION_HEADINGS.items():
            if pattern.match(stripped):
                matched_key = key
                rest = pattern.sub("", stripped).strip()
                if rest:
                    buckets[key].append(rest)
                break
        if matched_key:
            current = matched_key if matched_key != "summary" else "summary"
            if matched_key == "steps":
                current = "steps"
            elif matched_key == "escalation":
                current = "escalation"
            elif matched_key == "why":
                current = "why"
            continue

        bullet = re.match(r"^[-*•]\s+(.+)$", stripped)
        numbered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if current == "steps" and numbered:
            buckets["steps"].append(numbered.group(1).strip())
        elif current == "escalation" and (bullet or numbered):
            buckets["escalation"].append(
                (bullet or numbered).group(1).strip(),  # type: ignore[union-attr]
            )
        elif current == "steps" and bullet:
            buckets["steps"].append(bullet.group(1).strip())
        elif current == "escalation" and bullet:
            buckets["escalation"].append(bullet.group(1).strip())
        else:
            buckets[current].append(stripped)

    steps, escalation, why = _normalize_step_buckets(
        buckets["steps"],
        buckets["escalation"],
        buckets["why"],
    )
    if not steps:
        candidate = " ".join(buckets["summary"]).strip() or text
        derived_steps, derived_esc, derived_why = _split_step_payload(candidate)
        if derived_steps:
            steps = derived_steps
            escalation.extend(derived_esc)
            if derived_why and not why:
                why = derived_why
    if not steps:
        steps = parse_action_bullets(text)
        steps, extra_esc, extra_why = _normalize_step_buckets(steps, [], [])
        escalation.extend(extra_esc)
        if extra_why and not why:
            why = extra_why
    summary = " ".join(buckets["summary"]).strip()
    if not summary and steps:
        summary = steps[0][:200]
    elif not summary:
        summary = text.split("\n\n")[0][:240]

    if not why and steps:
        why = "Based on retrieved runbook, alert history, or postmortem in the Knowledge Base."

    return {
        "summary": summary,
        "steps": steps,
        "escalation": escalation,
        "why": why,
    }


def _format_json_alert_preview(data: dict[str, Any]) -> str:
    parts: list[str] = []
    alert_id = data.get("id", "")
    severity = data.get("severity", "")
    title = data.get("title", "")
    if alert_id or title:
        parts.append(f"Alert {alert_id} - {severity} - {title}".strip(" -"))
    fired = data.get("fired", "")
    if fired:
        parts.append(f"Fired: {fired}.")
    resolved = data.get("resolved_after_min")
    if resolved is not None:
        parts.append(f"Resolved after: {resolved} minutes.")
    pm = data.get("linked_postmortem") or data.get("runbook")
    if pm:
        parts.append(f"Linked document: {pm}.")
    summary = data.get("summary")
    if summary:
        parts.append(str(summary))
    return " ".join(parts)


def format_citation_preview(snippet: str, source_label: str = "", *, max_len: int = 220) -> str:
    """Turn raw chunk text (including JSON) into a readable citation preview."""
    text = (snippet or "").strip()
    if not text:
        return "No preview available."

    label_lower = (source_label or "").lower()
    if label_lower.endswith(".json") or text.startswith(("[", "{")):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list) and parsed:
                if isinstance(parsed[0], dict):
                    return _truncate(_format_json_alert_preview(parsed[0]), max_len)
                return _truncate(str(parsed[0]), max_len)
            if isinstance(parsed, dict):
                return _truncate(_format_json_alert_preview(parsed), max_len)
        except json.JSONDecodeError:
            pass

    if label_lower.endswith((".md", ".txt")):
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
                body = _first_meaningful_line(text, skip_headers=True)
                combined = f"{heading}. {body}" if body else heading
                return _truncate(combined, max_len)

    return _truncate(_first_meaningful_line(text) or text, max_len)


def _first_meaningful_line(text: str, *, skip_headers: bool = False) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("```"):
            continue
        if skip_headers and stripped.startswith("#"):
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            continue
        return stripped
    return ""


def _truncate(text: str, max_len: int) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def extract_reference_metadata(ref: dict[str, Any]) -> tuple[float | None, int | None]:
    """Pull relevance score and chunk index from Bedrock retrieved reference metadata."""
    score: float | None = None
    chunk_index: int | None = None

    meta = ref.get("metadata") or {}
    if isinstance(meta, dict):
        for key in ("score", "relevanceScore", "relevance_score"):
            if key in meta and meta[key] is not None:
                try:
                    score = float(meta[key])
                    break
                except (TypeError, ValueError):
                    pass
        for key in ("x-amz-bedrock-kb-chunk-id", "chunk_id", "chunk_index", "chunkIndex"):
            if key in meta and meta[key] is not None:
                raw = meta[key]
                if isinstance(raw, int):
                    chunk_index = raw
                elif isinstance(raw, str) and raw.isdigit():
                    chunk_index = int(raw)
                break

    if score is None and ref.get("score") is not None:
        try:
            score = float(ref["score"])
        except (TypeError, ValueError):
            pass

    return score, chunk_index
