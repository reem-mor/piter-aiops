import pytest

from app.bedrock_client import RagAnswer, Citation, MAX_QUESTION_LEN
from app.errors import BedrockError

pytestmark = pytest.mark.skip(
    reason="Legacy HTMX /ask and workflow routes archived; covered by SPA and /api/* tests.",
)


# ─── Index page ──────────────────────────────────────────────────────────────


def test_index_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"PITER AiOps" in response.data
    assert b"runbooks" in response.data


def test_index_shows_example_chips(client):
    response = client.get("/")
    assert b"auth" in response.data.lower()
    assert b'class="chip"' in response.data


def test_index_includes_htmx(client):
    response = client.get("/")
    assert b"hx-post" in response.data
    assert b"hx-target" in response.data


def test_index_includes_design_tokens(client):
    response = client.get("/")
    html = response.data.decode()
    assert "neon-ring-rag" in html
    assert 'id="architecture"' in html
    assert 'id="live-kb"' in html
    assert 'id="system-guide"' in html
    assert "data-open-guide" in html
    assert "workflow-stages" in html


# ─── /ask — input validation ─────────────────────────────────────────────────


def test_ask_empty_question_returns_400(client):
    response = client.post("/ask", data={"question": "   "})
    assert response.status_code == 400
    assert b"Please enter a question" in response.data


def test_ask_missing_question_field_returns_400(client):
    response = client.post("/ask", data={})
    assert response.status_code == 400


def test_ask_oversize_question_returns_400(client, fake_bedrock):
    response = client.post("/ask", data={"question": "x" * (MAX_QUESTION_LEN + 1)})
    assert response.status_code == 400
    assert b"too long" in response.data
    assert fake_bedrock.calls == []


def test_ask_stopwords_only_returns_400(client, fake_bedrock):
    response = client.post("/ask", data={"question": "what is the"})
    assert response.status_code == 400
    assert b"searchable keywords" in response.data
    assert fake_bedrock.calls == []


def test_ask_short_question_returns_400(client, fake_bedrock):
    response = client.post("/ask", data={"question": "ab"})
    assert response.status_code == 400
    assert b"at least 3 characters" in response.data
    assert fake_bedrock.calls == []


def test_ask_exact_max_length_is_accepted(client, fake_bedrock):
    fake_bedrock.next_response = RagAnswer(
        answer="ok", citations=[], session_id="s", grounded=False, latency_ms=1,
    )
    response = client.post("/ask", data={"question": "x" * MAX_QUESTION_LEN})
    assert response.status_code == 200
    assert len(fake_bedrock.calls) == 1


def test_ask_json_success(client, fake_bedrock):
    fake_bedrock.next_response = RagAnswer(
        answer="Restart the auth pod.",
        citations=[
            Citation(
                snippet="Restart auth pod.",
                source_uri="s3://kb/auth_runbook.md",
                source_label="auth_runbook.md",
                index=1,
            ),
        ],
        session_id="sess-1",
        grounded=True,
        latency_ms=42,
        matched_runbook="auth_runbook.md",
    )
    response = client.post(
        "/ask?format=json",
        json={"question": "How do I fix auth?"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["grounded"] is True
    assert data["latency_ms"] == 42
    assert data["citations"][0]["source_label"] == "auth_runbook.md"


def test_ask_json_validation_error(client, fake_bedrock):
    response = client.post(
        "/ask?format=json",
        json={"question": "ab"},
        content_type="application/json",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["ok"] is False
    assert data["reason"] == "short_question"
    assert fake_bedrock.calls == []


def test_ask_htmx_returns_html_even_with_json_accept(client, fake_bedrock):
    fake_bedrock.next_response = RagAnswer(
        answer="Restart the auth pod.",
        citations=[],
        session_id="sess-1",
        grounded=True,
        latency_ms=10,
    )
    response = client.post(
        "/ask",
        data={"question": "How do I fix auth?"},
        headers={"HX-Request": "true", "Accept": "application/json, text/html"},
    )
    assert response.status_code == 200
    assert "text/html" in response.content_type
    assert b"answer-card" in response.data
    assert response.get_json() is None


def test_ask_trims_surrounding_whitespace(client, fake_bedrock):
    fake_bedrock.next_response = RagAnswer(
        answer="ok", citations=[], session_id="s", grounded=False,
    )
    client.post("/ask", data={"question": "   hello there  "})
    assert fake_bedrock.calls == ["hello there"]


# ─── /ask — HTTP method enforcement ──────────────────────────────────────────


def test_ask_get_not_allowed(client):
    assert client.get("/ask").status_code == 405


# ─── /ask — happy path & grounded rendering ──────────────────────────────────


def test_ask_grounded_answer(client, fake_bedrock):
    fake_bedrock.next_response = RagAnswer(
        answer="Restart the auth pod and check the OIDC logs.",
        citations=[
            Citation(snippet="Restart auth pod via kubectl rollout restart.",
                     source_uri="s3://kb-bucket/auth_runbook.md"),
        ],
        session_id="sess-1",
        grounded=True,
    )
    response = client.post("/ask", data={"question": "How do I fix auth?"})
    assert response.status_code == 200
    assert b"Grounded" in response.data
    assert b"Restart the auth pod" in response.data
    assert b"auth_runbook.md" in response.data
    assert fake_bedrock.calls == ["How do I fix auth?"]


def test_ask_grounded_answer_pluralizes_sources(client, fake_bedrock):
    fake_bedrock.next_response = RagAnswer(
        answer="multi-source answer",
        citations=[
            Citation(snippet="chunk A", source_uri="s3://kb/a.md"),
            Citation(snippet="chunk B", source_uri="s3://kb/b.md"),
            Citation(snippet="chunk C", source_uri="s3://kb/c.md"),
        ],
        session_id="s", grounded=True,
    )
    response = client.post("/ask", data={"question": "How triage multiple sources?"})
    assert b"3 sources" in response.data


def test_ask_grounded_answer_singular_source(client, fake_bedrock):
    fake_bedrock.next_response = RagAnswer(
        answer="x",
        citations=[Citation(snippet="only one", source_uri="s3://kb/a.md", source_label="a.md")],
        session_id="s", grounded=True,
    )
    response = client.post("/ask", data={"question": "How triage auth issue?"})
    assert b"1 source" in response.data
    assert b"1 sources" not in response.data


# ─── /ask — no-match path ────────────────────────────────────────────────────


def test_ask_no_match_renders_amber_card(client, fake_bedrock):
    fake_bedrock.next_response = RagAnswer(
        answer="I could not find anything in the knowledge base for that question.",
        citations=[],
        session_id=None,
        grounded=False,
    )
    response = client.post("/ask", data={"question": "best pasta recipe?"})
    assert response.status_code == 200
    assert b"Not in knowledge base" in response.data


# ─── /ask — error mapping ────────────────────────────────────────────────────


def test_ask_bedrock_throttling_returns_502(client, fake_bedrock):
    fake_bedrock.next_error = BedrockError(
        "Bedrock is throttling requests.", code="ThrottlingException",
    )
    response = client.post("/ask", data={"question": "anything"})
    assert response.status_code == 502
    assert b"throttling" in response.data.lower()


def test_ask_bedrock_access_denied_returns_502(client, fake_bedrock):
    fake_bedrock.next_error = BedrockError(
        "Not authorized", code="AccessDeniedException",
    )
    response = client.post("/ask", data={"question": "anything"})
    assert response.status_code == 502
    assert b"Not authorized" in response.data


# ─── /ask — output safety ────────────────────────────────────────────────────


def test_ask_escapes_html_in_question(client, fake_bedrock):
    """Jinja autoescape must protect against XSS via the echoed question."""
    fake_bedrock.next_response = RagAnswer(
        answer="ok", citations=[], session_id="s", grounded=False,
    )
    response = client.post(
        "/ask", data={"question": "<script>alert('xss')</script>"},
    )
    assert response.status_code == 200
    assert b"<script>alert" not in response.data
    assert b"&lt;script&gt;" in response.data


def test_ask_escapes_html_in_answer(client, fake_bedrock):
    fake_bedrock.next_response = RagAnswer(
        answer="<img src=x onerror=alert(1)>",
        citations=[], session_id="s", grounded=False,
    )
    response = client.post("/ask", data={"question": "anything"})
    assert b"<img src=x" not in response.data
    assert b"&lt;img" in response.data


def test_ask_handles_unicode_question(client, fake_bedrock):
    fake_bedrock.next_response = RagAnswer(
        answer="שלום", citations=[], session_id="s", grounded=False,
    )
    response = client.post(
        "/ask", data={"question": "שלום, what is the auth runbook?"},
    )
    assert response.status_code == 200
    assert "שלום".encode("utf-8") in response.data


# ─── /health & method enforcement ────────────────────────────────────────────


def test_health_post_not_allowed(client):
    assert client.post("/health").status_code == 405


# ─── /404 ────────────────────────────────────────────────────────────────────


def test_workflow_triage_renders_result(client, fake_bedrock):
    fake_bedrock.next_response = RagAnswer(
        answer="- Check logs\n- Roll back deploy",
        citations=[
            Citation(
                snippet="rollback steps",
                source_uri="s3://kb/api_gateway_5xx_runbook.txt",
                source_label="api_gateway_5xx_runbook.txt",
            ),
        ],
        session_id="s",
        grounded=True,
        matched_runbook="api_gateway_5xx_runbook.txt",
    )
    response = client.post(
        "/workflow/triage",
        data={"alert_id": "A-2042", "question": "What should I do for API 5xx errors?"},
    )
    assert response.status_code == 200
    assert b"api_gateway_5xx_runbook.txt" in response.data
    assert b"Check logs" in response.data
    assert b"Recommendation:" in response.data
    assert b"Impact avoided" in response.data


def test_unknown_route_returns_404_or_spa_fallback(client, app):
    response = client.get("/no-such-path")
    from app.spa import spa_index_path

    if spa_index_path() and not app.config.get("FORCE_LEGACY_UI"):
        assert response.status_code == 200
        assert b'id="root"' in response.data
    else:
        assert response.status_code == 404
