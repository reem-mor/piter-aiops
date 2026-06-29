"""Environment code normalization and validation."""
from __future__ import annotations

import pytest

from app.environment_codes import normalize_environment, validate_environment


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("GIB-UKGC", "GIB-UKGC"),
        ("nj-dge", "NJ-DGE"),
        ("MGM", "MGM"),
        ("MIRAGE", "MIRAGE"),
        ("GIB", "GIB-UKGC"),
        ("NJ", "NJ-DGE"),
    ],
)
def test_normalize_environment(raw: str, expected: str):
    assert normalize_environment(raw) == expected


def test_validate_accepts_canonical_codes():
    for env in ("GIB-UKGC", "NJ-DGE", "MGM", "MIRAGE"):
        canonical, err = validate_environment(env)
        assert err is None
        assert canonical == env


def test_validate_accepts_aliases():
    canonical, err = validate_environment("GIB")
    assert err is None
    assert canonical == "GIB-UKGC"
    canonical, err = validate_environment("NJ")
    assert err is None
    assert canonical == "NJ-DGE"


def test_validate_rejects_unknown_environment():
    canonical, err = validate_environment("INVALID")
    assert canonical is None
    assert err is not None
    assert "Unknown environment" in err
    assert "GIB-UKGC" in err
