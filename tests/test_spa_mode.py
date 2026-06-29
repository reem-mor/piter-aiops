"""Tests for production SPA + JSON API (FORCE_LEGACY_UI off)."""
from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app
from app.bedrock_client import Citation, RagAnswer
from app.config import Config

SPA_INDEX = Path(__file__).resolve().parents[1] / "app" / "static" / "spa" / "index.html"


def _fake_answer():
    return RagAnswer(
        answer="Grounded answer.",
        citations=[
            Citation(
                snippet="snippet",
                source_uri="s3://b/runbook.md",
                source_label="runbook.md",
                index=1,
            )
        ],
        session_id="sess-follow",
        grounded=True,
        latency_ms=50,
        matched_runbook="runbook.md",
    )


@pytest.fixture
def spa_client(fake_config, fake_bedrock):
    if not SPA_INDEX.is_file():
        pytest.skip("SPA build missing — run: cd frontend && npm run build")
    app = create_app(fake_config)
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        FORCE_LEGACY_UI=False,
    )
    app.extensions["bedrock_client"] = fake_bedrock
    return app.test_client()


def test_spa_home_serves_index(spa_client):
    response = spa_client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'id="root"' in body or "root" in body


def test_console_redirects_to_spa(spa_client):
    response = spa_client.get("/console")
    assert response.status_code in {302, 307}
    assert response.headers.get("Location") == "/"


def test_get_ask_returns_405_in_spa_mode(spa_client):
    assert spa_client.get("/ask").status_code == 405


def test_bootstrap_example_groups_is_dict(spa_client):
    data = spa_client.get("/api/bootstrap").get_json()
    assert data["ok"] is True
    assert isinstance(data["example_groups"], dict)
    assert len(data["example_groups"]) >= 1


def test_chat_accepts_session_id(spa_client, fake_bedrock):
    fake_bedrock.next_response = _fake_answer()
    response = spa_client.post(
        "/api/chat",
        json={"message": "How do I triage an authentication service incident?", "session_id": "sess-abc"},
    )
    assert response.status_code == 200
    assert fake_bedrock.last_session_id == "sess-abc"
    data = response.get_json()
    assert data.get("session_id") == "sess-follow" or data.get("memory", {}).get("session_id")


def test_health_deep(spa_client):
    data = spa_client.get("/health?deep=1").get_json()
    assert data["status"] in {"ok", "degraded"}
    assert "checks" in data


def test_bootstrap_exposes_alert_stream_and_execution_hint(spa_client):
    data = spa_client.get("/api/bootstrap").get_json()
    stream = data.get("alert_stream") or {}
    assert 390 <= stream.get("total", 0) <= 400
    assert "400" in stream.get("label", "") or stream.get("total") == 400
    assert data.get("execution_mode_hint")
    assert data.get("notification", {}).get("mode") in {"mock", "preview", "live"}


def test_spa_assets_reference_noc_shell(spa_client):
    assets = Path(__file__).resolve().parents[1] / "app" / "static" / "spa" / "assets"
    js_files = list(assets.glob("index-*.js"))
    if not js_files:
        pytest.skip("SPA JS bundle missing")
    bundle = js_files[0].read_text(encoding="utf-8")
    assert "PITER" in bundle
    assert "Operations Dashboard" in bundle or "Incident Analyzer" in bundle
    assert "Start Alert Stream" in bundle or "Agent Chat" in bundle
    assert "/api/health" in bundle or "api/health" in bundle
