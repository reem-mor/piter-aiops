"""Tests for the canonical data layer (app/services/data_access.py).

All structured datasets are read from data/source/ only; the legacy
agent_data/ and top-level demo files have been quarantined to data/archive/.
"""
from __future__ import annotations

import json

import pytest

from app.services import data_access as da
from app.services.data_access import DataAccessError


def test_load_source_deploys_valid():
    rows = da.load_source_deploys()
    assert len(rows) >= 1
    assert da.SOURCE_DEPLOYS_COLUMNS <= set(rows[0].keys())


def test_load_service_owners_valid():
    rows = da.load_service_owners()
    names = {r["service"] for r in rows}
    assert {"bet-service", "auth-service", "wallet-service"} <= names
    assert da.SERVICE_OWNERS_COLUMNS <= set(rows[0].keys())


def test_load_business_impact_has_services():
    data = da.load_business_impact()
    assert "bet-service" in data["services"]
    assert data["services"]["bet-service"]["p1_cost_per_minute_usd"] == 9800


def test_load_priority_matrix_thresholds():
    matrix = da.load_priority_matrix()
    assert "P1" in matrix["thresholds"]


def test_load_escalation_policies_default():
    policies = da.load_escalation_policies()
    assert "P1" in policies["default_policy"]


def test_load_past_incidents_valid():
    rows = da.load_past_incidents()
    assert len(rows) >= 30
    assert da.PAST_INCIDENTS_COLUMNS <= set(rows[0].keys())


def test_load_on_call_schedule_valid():
    rows = da.load_on_call_schedule()
    assert len(rows) >= 1


def test_resolve_alert_by_service_and_env():
    alert = da.resolve_alert(service="bet-service", environment="GIB-UKGC")
    assert alert is not None
    assert alert["service"] == "bet-service"


def test_missing_csv_raises(tmp_path):
    with pytest.raises(DataAccessError):
        da.load_service_owners(source_dir=str(tmp_path))


def test_missing_columns_raises(tmp_path):
    bad = tmp_path / "deploys.csv"
    bad.write_text("foo,bar\n1,2\n", encoding="utf-8")
    with pytest.raises(DataAccessError) as exc:
        da._read_csv_rows(bad, da.SOURCE_DEPLOYS_COLUMNS)
    assert "missing required columns" in str(exc.value)


def test_malformed_json_raises(tmp_path):
    bad = tmp_path / "business_impact.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(DataAccessError) as exc:
        da.load_business_impact(source_dir=str(tmp_path))
    assert "Malformed JSON" in str(exc.value)


def test_json_wrong_shape_raises(tmp_path):
    bad = tmp_path / "business_impact.json"
    bad.write_text(json.dumps({"nope": []}), encoding="utf-8")
    with pytest.raises(DataAccessError):
        da.load_business_impact(source_dir=str(tmp_path))
