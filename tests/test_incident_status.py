"""Operator status overrides: POST /api/incidents/<id>/status + merge into investigations."""

import pytest

from app.services import incident_status


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path):
    incident_status.set_store_path(tmp_path / "incident_status.json")
    yield
    incident_status.set_store_path(tmp_path / "incident_status_reset.json")


def test_post_status_persists(client):
    response = client.post("/api/incidents/INC-001/status", json={"status": "in_process"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["incident_id"] == "INC-001"
    assert data["status"] == "in_process"
    assert incident_status.get_status("INC-001") == "in_process"


def test_post_status_rejects_unknown_value(client):
    response = client.post("/api/incidents/INC-001/status", json={"status": "bogus"})
    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_status_survives_reload(client, tmp_path):
    store = tmp_path / "incident_status.json"
    incident_status.set_store_path(store)
    client.post("/api/incidents/INC-009/status", json={"status": "resolved"})
    # Simulate a fresh process: force the module to re-read from disk.
    incident_status.set_store_path(store)
    assert incident_status.get_status("INC-009") == "resolved"


def test_investigations_include_operator_status(client):
    inv = client.get("/api/investigations?limit=5").get_json()
    cards = inv.get("investigations") or []
    if not cards:
        pytest.skip("no investigation cards in test dataset")
    target = str(cards[0]["id"])
    client.post(f"/api/incidents/{target}/status", json={"status": "in_process"})
    inv2 = client.get("/api/investigations?limit=5").get_json()
    merged = {str(c["id"]): c for c in inv2["investigations"]}
    assert merged[target].get("operator_status") == "in_process"
