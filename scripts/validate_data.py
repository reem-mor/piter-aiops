#!/usr/bin/env python3
"""Validate the canonical PITER AiOps datasets under ``data/source/``.

Loads every structured dataset through the schema-validating loaders in
:mod:`app.services.data_access` and asserts that the legacy runtime paths have
been quarantined to ``data/archive/``. Exits non-zero on any missing file,
schema violation, or stray legacy path so CI and the pre-demo checklist fail
loudly.

Usage:
    python scripts/validate_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from app.services import data_access as da  # noqa: E402

SOURCE = _ROOT / "data" / "source"

# Canonical files the four tools + data layer read (KEEP under data/source/).
EXPECTED_FILES = {
    "alert_stream.csv",
    "alerts.csv",
    "service_owners.csv",
    "on_call_schedule.csv",
    "past_incidents.csv",
    "deploys.csv",
    "business_impact.json",
    "priority_matrix.json",
    "escalation_policies.json",
}

# Legacy runtime paths that must NOT exist anymore (quarantined to data/archive/).
FORBIDDEN_LEGACY = (
    _ROOT / "data" / "agent_data",
    _ROOT / "data" / "deployments.csv",
    _ROOT / "data" / "historical_incidents.csv",
    _ROOT / "data" / "services.json",
    _ROOT / "data" / "external_status.json",
    _ROOT / "data" / "sample_documents",
)

# Loader -> human label, exercising the canonical data/source/ read path.
LOADERS = (
    ("alert_stream.csv", lambda: da.load_source_alert_stream()),
    ("alerts.csv", lambda: da.load_source_alerts()),
    ("service_owners.csv", lambda: da.load_service_owners()),
    ("on_call_schedule.csv", lambda: da.load_on_call_schedule()),
    ("past_incidents.csv", lambda: da.load_past_incidents()),
    ("deploys.csv", lambda: da.load_source_deploys()),
    ("business_impact.json", lambda: da.load_business_impact()),
    ("priority_matrix.json", lambda: da.load_priority_matrix()),
    ("escalation_policies.json", lambda: da.load_escalation_policies()),
)


def _check_files() -> list[str]:
    errors: list[str] = []
    if not SOURCE.is_dir():
        return [f"data/source/ is missing: {SOURCE}"]
    present = {p.name for p in SOURCE.iterdir() if p.is_file()}
    for name in sorted(EXPECTED_FILES - present):
        errors.append(f"missing canonical file: data/source/{name}")
    for legacy in FORBIDDEN_LEGACY:
        if legacy.exists():
            errors.append(
                f"legacy runtime path still present (should be quarantined to "
                f"data/archive/): {legacy.relative_to(_ROOT)}"
            )
    return errors


def _check_schemas() -> list[str]:
    errors: list[str] = []
    for name, loader in LOADERS:
        try:
            data = loader()
            count = len(data) if isinstance(data, list) else len(data.get("services", data))
            print(f"  OK   {name:<26} ({count} records)")
        except Exception as exc:  # noqa: BLE001 — report every dataset's status
            errors.append(f"{name}: {exc}")
            print(f"  FAIL {name:<26} {exc}")
    return errors


def main() -> int:
    print(f"Validating canonical data dir: {SOURCE}")
    print(f"pandas engine available: {da.pandas_available()}")
    file_errors = _check_files()
    if file_errors:
        for err in file_errors:
            print(f"  FAIL {err}")
        print("\nDATA VALIDATION FAILED")
        return 1
    print("\nSchema validation (via data/source loaders):")
    schema_errors = _check_schemas()
    if schema_errors:
        print(f"\nDATA VALIDATION FAILED ({len(schema_errors)} error(s))")
        return 1
    print("\nDATA VALIDATION PASSED — all four tools read only data/source/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
