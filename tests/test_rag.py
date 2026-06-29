"""Tests for the offline local RAG retriever and LocalRagClient."""
from __future__ import annotations

from app.local_agent import LocalRagClient
from app.services.local_rag import LocalRetriever, get_retriever


def test_retriever_indexes_runbooks():
    r = get_retriever()
    assert r.runbook_dir.name == "knowledge_base"
    assert r.document_count() >= 10


def test_search_returns_db_cpu_runbook_for_demo_query():
    hits = get_retriever().search("Postgres CPU is 95% on prod-db-1 what is the runbook", top_k=3)
    assert hits
    assert hits[0].document == "database_connectivity.json"
    assert hits[0].score > 0


def test_search_returns_auth_runbook():
    hits = get_retriever().search("authentication login failures users cannot log in error rate", top_k=3)
    assert any("auth_service_login_failure" in h.document for h in hits)


def test_local_client_answer_is_grounded_and_cited():
    client = LocalRagClient()
    ans = client.ask("Postgres CPU is 95% on prod-db-1 — what is the runbook?")
    assert ans.grounded is True
    assert ans.mode == "local"
    assert ans.citations
    assert ans.matched_runbook == "database_connectivity.json"
    payload = ans.to_dict()
    assert payload["citations"][0]["source_label"] == "database_connectivity.json"


def test_local_client_refuses_off_topic():
    client = LocalRagClient()
    ans = client.ask("What is the best restaurant in Tokyo right now?")
    assert ans.grounded is False
    assert "Not in knowledge base" in ans.answer


def test_retriever_empty_dir(tmp_path):
    empty = LocalRetriever(runbook_dir=tmp_path)
    assert empty.search("anything", top_k=3) == []
