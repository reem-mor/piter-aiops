"""Severity-based demo business impact estimates (archived module)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_MOD = Path(__file__).resolve().parents[1] / "archive" / "legacy-htmx" / "workflow_impact.py"
_spec = importlib.util.spec_from_file_location("legacy_workflow_impact", _MOD)
assert _spec and _spec.loader
_legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_legacy)
severity_impact = _legacy.severity_impact
SEVERITY_IMPACT = _legacy.SEVERITY_IMPACT


def test_severity_impact_table():
    assert severity_impact("P1") == (30, 5000)
    assert severity_impact("P2") == (15, 2500)
    assert severity_impact("P3") == (5, 500)


def test_severity_impact_defaults_to_p3():
    assert severity_impact(None) == SEVERITY_IMPACT["P3"]
    assert severity_impact("unknown") == SEVERITY_IMPACT["P3"]
