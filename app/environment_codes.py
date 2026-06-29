"""Canonical environment codes and optional aliases for demo datasets and tools."""
from __future__ import annotations

CANONICAL_ENVIRONMENTS: frozenset[str] = frozenset(
    {"GIB-UKGC", "NJ-DGE", "MGM", "MIRAGE"}
)

_ENV_ALIASES: dict[str, str] = {
    "GIB": "GIB-UKGC",
    "NJ": "NJ-DGE",
    "DGE": "NJ-DGE",
    "UKGC": "GIB-UKGC",
    "GBGA": "GIB-UKGC",
}


def normalize_environment(raw: str | None) -> str:
    """Return canonical environment code; pass through unknown values uppercased."""
    token = (raw or "").strip().upper()
    if not token:
        return ""
    if token in CANONICAL_ENVIRONMENTS:
        return token
    return _ENV_ALIASES.get(token, token)


def validate_environment(raw: str | None) -> tuple[str | None, str | None]:
    """Validate and normalize an environment code.

    Returns ``(canonical, None)`` on success or ``(None, error_message)`` on failure.
    """
    token = (raw or "").strip()
    if not token:
        return None, "environment is required"
    canonical = normalize_environment(token)
    if canonical not in CANONICAL_ENVIRONMENTS:
        allowed = ", ".join(sorted(CANONICAL_ENVIRONMENTS))
        return None, (
            f"Unknown environment '{token}'. "
            f"Use one of: {allowed} (aliases: GIB, NJ)."
        )
    return canonical, None
