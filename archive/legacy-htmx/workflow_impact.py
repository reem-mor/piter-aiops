"""Demo severity-based business impact estimates for workflow triage."""
from __future__ import annotations

# Demo estimates only — not real financial figures.
SEVERITY_IMPACT: dict[str, tuple[int, int]] = {
    "P1": (30, 5000),
    "P2": (15, 2500),
    "P3": (5, 500),
}


def severity_impact(severity: str | None) -> tuple[int, int]:
    """Return (mttr_minutes_avoided, dollars_avoided) for a severity label."""
    key = (severity or "P3").upper()
    return SEVERITY_IMPACT.get(key, SEVERITY_IMPACT["P3"])
