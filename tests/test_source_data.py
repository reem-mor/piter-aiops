"""Validate canonical structured source data and generators."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source"
SCRIPTS = ROOT / "scripts"
KB_RUNBOOKS = ROOT / "knowledge_base" / "runbooks"

EXPECTED_FILES = {
    "alerts.csv",
    "alert_stream.csv",
    "business_impact.json",
    "deploys.csv",
    "escalation_policies.json",
    "on_call_schedule.csv",
    "past_incidents.csv",
    "priority_matrix.json",
    "service_owners.csv",
}


def _csv_rows(name: str) -> list[dict[str, str]]:
    with (SOURCE / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_source_data_files_exist():
    assert EXPECTED_FILES <= {path.name for path in SOURCE.iterdir() if path.is_file()}


def test_source_data_core_schemas_and_demo_rows():
    alerts = _csv_rows("alerts.csv")
    assert {"alert_id", "timestamp", "environment", "service", "severity"} <= set(alerts[0])
    assert any(row["alert_id"] == "ALERT-SUM-001" for row in alerts)

    deploys = _csv_rows("deploys.csv")
    assert {"deploy_id", "timestamp", "environment", "service", "rollback_available"} <= set(deploys[0])
    assert any(
        row["deploy_id"] == "DEP-2026-06-003"
        and row["service"] == "wallet-service"
        and row["environment"] == "GIB-UKGC"
        for row in deploys
    )

    incidents = _csv_rows("past_incidents.csv")
    assert {"incident_id", "service", "root_cause", "resolution", "mttr_minutes"} <= set(incidents[0])


def test_source_json_references_cover_services():
    service_rows = _csv_rows("service_owners.csv")
    services = {row["service"] for row in service_rows}

    impact = json.loads((SOURCE / "business_impact.json").read_text(encoding="utf-8"))
    assert services <= set(impact["services"])

    priority = json.loads((SOURCE / "priority_matrix.json").read_text(encoding="utf-8"))
    assert {"P1", "P2", "P3", "P4"} <= set(priority["thresholds"])


def test_alert_stream_row_count_and_single_p1_trigger():
    stream = _csv_rows("alert_stream.csv")
    assert len(stream) == 400
    p1_triggers = [
        row for row in stream
        if row.get("is_trigger", "").lower() == "true" or row.get("severity", "").upper() == "P1"
    ]
    assert len([r for r in stream if r.get("is_trigger", "").lower() == "true"]) == 1
    assert any(row["alert_id"] == "ALT-2026-06-10-0251" for row in p1_triggers)


def test_source_services_subset_of_service_owners():
    owners = {row["service"] for row in _csv_rows("service_owners.csv")}
    for name in ("alert_stream.csv", "deploys.csv", "past_incidents.csv"):
        services = {row["service"] for row in _csv_rows(name)}
        assert services <= owners, f"{name} references unknown services"


def test_all_runbook_references_exist_in_kb():
    runbooks = {path.name for path in KB_RUNBOOKS.glob("*.json")}
    refs: set[str] = set()
    for row in _csv_rows("service_owners.csv"):
        if row.get("runbook"):
            refs.add(row["runbook"].strip())
    for row in _csv_rows("past_incidents.csv"):
        if row.get("related_runbook"):
            refs.add(row["related_runbook"].strip())
    missing = refs - runbooks
    assert not missing, f"Missing KB runbooks: {sorted(missing)}"


def test_source_data_does_not_include_direct_recipient_contacts():
    text = "\n".join(path.read_text(encoding="utf-8") for path in SOURCE.glob("*.csv"))
    text += "\n".join(path.read_text(encoding="utf-8") for path in SOURCE.glob("*.json"))
    assert "@" not in text
    assert "+1" not in text


def test_generators_default_to_project_source_and_support_output(tmp_path):
    for script in ("generate_demo_data.py", "generate_alert_stream.py"):
        content = (SCRIPTS / script).read_text(encoding="utf-8")
        assert "/home/claude/piter_data" not in content
        assert "DEFAULT_OUTPUT = PROJECT_ROOT / \"data\" / \"source\"" in content

    out = tmp_path / "generated"
    subprocess.run(
        [sys.executable, str(SCRIPTS / "generate_demo_data.py"), "--output", str(out)],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [sys.executable, str(SCRIPTS / "generate_alert_stream.py"), "--output", str(out)],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert EXPECTED_FILES <= {path.name for path in out.iterdir() if path.is_file()}
    generated_alerts = list(csv.DictReader((out / "alert_stream.csv").open(newline="", encoding="utf-8")))
    assert 390 <= len(generated_alerts) <= 400
    assert any(row["alert_id"] == "ALT-DEMO-P1-001" for row in generated_alerts)
