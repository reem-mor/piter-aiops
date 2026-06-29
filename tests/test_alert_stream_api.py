"""Tests for GET /api/alert-stream and bootstrap alert_stream summary."""
from __future__ import annotations

from app import create_app


def test_alert_stream_summary(client):
    response = client.get("/api/alert-stream")
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert 390 <= data["total"] <= 400
    assert "399" in data["label"] or str(data["total"]) in data["label"]
    assert data["noise_suppressed"] >= 0
    assert data["p1_count"] >= 1
    assert data.get("p1_trigger")


def test_alert_stream_include_rows(client):
    response = client.get("/api/alert-stream?include_rows=true")
    data = response.get_json()
    assert response.status_code == 200
    rows = data.get("rows") or []
    assert len(rows) == data["total"]


def test_bootstrap_includes_alert_stream(client):
    data = client.get("/api/bootstrap").get_json()
    assert data["ok"] is True
    stream = data.get("alert_stream") or {}
    assert 390 <= stream.get("total", 0) <= 400
    assert data.get("execution_mode_hint")
    assert data.get("notification", {}).get("mode") in {"mock", "preview", "live"}
