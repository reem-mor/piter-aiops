"""Typed, validated loaders for the PITER AiOps data layer (Pandas + CSV + JSON).

Centralizes access to the CSV/JSON operational datasets so the tools and the
local agent share one schema-validated source of truth. Each loader raises a
clear :class:`DataAccessError` on a missing file, missing column, or malformed
JSON/CSV instead of leaking a raw traceback.

Pandas is the preferred CSV engine and is used whenever it is importable
(Docker/Linux/CI). On hardened hosts where the compiled numpy/pandas binaries
are blocked, the loaders fall back to the standard-library ``csv`` module and
return the same ``list[dict]`` shape, so the local demo and tests never break.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.environment_codes import normalize_environment

# Canonical structured data lives under data/source/ ONLY. Legacy
# data/agent_data/, top-level demo CSV/JSON, and data/sample_documents/ paths
# have been quarantined to data/archive/ and are no longer read here.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SOURCE_DATA = _PROJECT_ROOT / "data" / "source"
_KB_RUNBOOKS = _PROJECT_ROOT / "knowledge_base" / "runbooks"

SOURCE_DEPLOYS_COLUMNS = {
    "deploy_id",
    "timestamp",
    "environment",
    "service",
    "version",
    "status",
    "change_summary",
    "risk_level",
    "rollback_available",
}
SERVICE_OWNERS_COLUMNS = {
    "service",
    "owning_team",
    "service_tier",
    "business_function",
    "slack_channel",
    "primary_on_call_role",
    "secondary_on_call_role",
    "runbook",
    "dashboard",
    "dependencies",
    "regulatory_exposure",
}
PAST_INCIDENTS_COLUMNS = {
    "incident_id",
    "service",
    "environment",
    "severity",
    "root_cause",
    "resolution",
    "mttr_minutes",
    "lessons_learned",
    "related_runbook",
}
ALERT_STREAM_COLUMNS = {
    "alert_id",
    "timestamp",
    "environment",
    "service",
    "severity",
    "title",
}
SOURCE_ALERTS_COLUMNS = {
    "alert_id",
    "timestamp",
    "environment",
    "service",
    "severity",
    "title",
}


class DataAccessError(RuntimeError):
    """Raised when a dataset is missing, malformed, or fails schema validation."""


# Memoize the pandas import. On hardened hosts the blocked numpy DLL makes each
# import attempt slow, so we try exactly once per process. ``False`` means
# "tried and unavailable"; ``None`` means "not tried yet".
_PANDAS_MODULE: Any = None
_PANDAS_TRIED = False

# In-process cache for static demo datasets (keyed by path + mtime).
_CSV_CACHE: dict[str, tuple[float, list[dict[str, str]]]] = {}
_JSON_CACHE: dict[str, tuple[float, Any]] = {}


def reset_data_cache() -> None:
    """Clear cached CSV/JSON loads (tests and demo reload)."""
    _CSV_CACHE.clear()
    _JSON_CACHE.clear()


def _get_pandas():
    """Return the pandas module if importable here, else ``None`` (memoized)."""
    global _PANDAS_MODULE, _PANDAS_TRIED
    if not _PANDAS_TRIED:
        _PANDAS_TRIED = True
        try:
            import pandas as pd  # noqa: WPS433 — optional, lazily imported once
        except ImportError:
            _PANDAS_MODULE = None
        else:
            _PANDAS_MODULE = pd
    return _PANDAS_MODULE


def pandas_available() -> bool:
    """Return True when pandas (and its numpy backend) can be imported here."""
    return _get_pandas() is not None


def _read_csv_rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    """Read a CSV into a list of dict rows, validating required columns.

    Uses pandas when available, otherwise the stdlib ``csv`` module. Both paths
    return identical ``list[dict[str, str]]`` output.
    """
    if not path.is_file():
        raise DataAccessError(f"Missing data file: {path.name}")
    resolved = path.resolve()
    cache_key = str(resolved)
    mtime = resolved.stat().st_mtime
    cached = _CSV_CACHE.get(cache_key)
    if cached and cached[0] == mtime:
        return cached[1]
    pd = _get_pandas()
    if pd is None:
        rows = _read_csv_stdlib(path, required)
    else:
        try:
            frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        except pd.errors.EmptyDataError as exc:
            raise DataAccessError(f"Data file is empty: {path.name}") from exc
        except pd.errors.ParserError as exc:
            raise DataAccessError(f"Malformed CSV: {path.name} ({exc})") from exc
        missing = required - set(frame.columns)
        if missing:
            raise DataAccessError(
                f"{path.name} is missing required columns: {sorted(missing)}"
            )
        rows = frame.to_dict("records")
    _CSV_CACHE[cache_key] = (mtime, rows)
    return rows


def _read_csv_stdlib(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise DataAccessError(f"Data file is empty: {path.name}")
        missing = required - set(reader.fieldnames)
        if missing:
            raise DataAccessError(
                f"{path.name} is missing required columns: {sorted(missing)}"
            )
        return [dict(row) for row in reader]


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise DataAccessError(f"Missing data file: {path.name}")
    resolved = path.resolve()
    cache_key = str(resolved)
    mtime = resolved.stat().st_mtime
    cached = _JSON_CACHE.get(cache_key)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataAccessError(f"Malformed JSON: {path.name} ({exc})") from exc
    _JSON_CACHE[cache_key] = (mtime, payload)
    return payload


def source_data_dir() -> Path:
    """Return the canonical structured dataset directory."""
    return _SOURCE_DATA


def list_runbook_files() -> set[str]:
    """Return runbook filenames present under knowledge_base/runbooks/."""
    if not _KB_RUNBOOKS.is_dir():
        return set()
    return {
        path.name
        for path in _KB_RUNBOOKS.rglob("*.json")
        if path.is_file() and path.suffix == ".json"
    }


def load_source_alert_stream(source_dir: str | Path | None = None) -> list[dict[str, str]]:
    base = Path(source_dir) if source_dir else _SOURCE_DATA
    return _read_csv_rows(base / "alert_stream.csv", ALERT_STREAM_COLUMNS)


def load_source_alerts(source_dir: str | Path | None = None) -> list[dict[str, str]]:
    base = Path(source_dir) if source_dir else _SOURCE_DATA
    return _read_csv_rows(base / "alerts.csv", SOURCE_ALERTS_COLUMNS)


def load_service_owners(source_dir: str | Path | None = None) -> list[dict[str, str]]:
    base = Path(source_dir) if source_dir else _SOURCE_DATA
    return _read_csv_rows(base / "service_owners.csv", SERVICE_OWNERS_COLUMNS)


def load_source_deploys(source_dir: str | Path | None = None) -> list[dict[str, str]]:
    base = Path(source_dir) if source_dir else _SOURCE_DATA
    return _read_csv_rows(base / "deploys.csv", SOURCE_DEPLOYS_COLUMNS)


def load_business_impact(source_dir: str | Path | None = None) -> dict[str, Any]:
    base = Path(source_dir) if source_dir else _SOURCE_DATA
    data = _read_json(base / "business_impact.json")
    if not isinstance(data, dict) or "services" not in data:
        raise DataAccessError("business_impact.json must contain a 'services' object")
    return data


def load_priority_matrix(source_dir: str | Path | None = None) -> dict[str, Any]:
    base = Path(source_dir) if source_dir else _SOURCE_DATA
    data = _read_json(base / "priority_matrix.json")
    if not isinstance(data, dict) or "thresholds" not in data:
        raise DataAccessError("priority_matrix.json must contain 'thresholds'")
    return data


def load_escalation_policies(source_dir: str | Path | None = None) -> dict[str, Any]:
    base = Path(source_dir) if source_dir else _SOURCE_DATA
    data = _read_json(base / "escalation_policies.json")
    if not isinstance(data, dict) or "default_policy" not in data:
        raise DataAccessError("escalation_policies.json must contain 'default_policy'")
    return data


def load_past_incidents(source_dir: str | Path | None = None) -> list[dict[str, str]]:
    base = Path(source_dir) if source_dir else _SOURCE_DATA
    return _read_csv_rows(base / "past_incidents.csv", PAST_INCIDENTS_COLUMNS)


def load_on_call_schedule(source_dir: str | Path | None = None) -> list[dict[str, str]]:
    base = Path(source_dir) if source_dir else _SOURCE_DATA
    path = base / "on_call_schedule.csv"
    if not path.is_file():
        raise DataAccessError("Missing data file: on_call_schedule.csv")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def resolve_alert(
    *,
    alert_id: str = "",
    service: str = "",
    environment: str = "",
    source_dir: str | Path | None = None,
) -> dict[str, str] | None:
    """Resolve an alert from alert_stream, summary alerts, or service+env match."""
    base = Path(source_dir) if source_dir else _SOURCE_DATA
    aid = (alert_id or "").strip()
    svc = (service or "").strip().lower()
    env = normalize_environment(environment)

    if aid:
        for row in load_source_alert_stream(base):
            if row.get("alert_id") == aid:
                return dict(row)
        for row in load_source_alerts(base):
            if row.get("alert_id") == aid:
                return dict(row)

    if svc and env:
        for row in load_source_alert_stream(base):
            if (
                row.get("service", "").lower() == svc
                and normalize_environment(row.get("environment", "")) == env
                and row.get("is_trigger", "").lower() == "true"
            ):
                return dict(row)
        for row in load_source_alerts(base):
            if (
                row.get("service", "").lower() == svc
                and normalize_environment(row.get("environment", "")) == env
            ):
                return dict(row)

    return None
