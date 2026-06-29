"""Unit tests for BedrockAgentClient — mock invoke_agent event stream, no AWS."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.bedrock_agent_client import BedrockAgentClient
from app.config import Config


@pytest.fixture
def agent_config():
    return Config(
        AWS_REGION="us-east-1",
        BEDROCK_KB_ID="KBTEST1234",
        BEDROCK_MODEL_ARN="arn:aws:bedrock:us-east-1::foundation-model/test",
        BEDROCK_NUM_RESULTS=5,
        SECRET_KEY="x",
        FLASK_ENV="testing",
        BEDROCK_AGENT_ID="AGENT123",
        BEDROCK_AGENT_ALIAS_ID="ALIAS456",
        RAG_BACKEND="agent",
    )


def _stream(events: list[dict]):
    return {"completion": events, "sessionId": "sess-agent-1"}


def _rag_response(*, text: str = "", uri: str | None = None) -> dict:
    citations = []
    if uri:
        citations = [
            {
                "retrievedReferences": [
                    {
                        "content": {"text": "Runbook excerpt."},
                        "location": {"s3Location": {"uri": uri}},
                    }
                ]
            }
        ]
    return {"output": {"text": text}, "citations": citations, "sessionId": "sess-rag-1"}


def _mock_ungrounded_rag(mock_client: MagicMock) -> None:
    mock_client.retrieve_and_generate.return_value = _rag_response(text="No KB match.")


def _mock_grounded_rag(mock_client: MagicMock, *, text: str, uri: str) -> None:
    mock_client.retrieve_and_generate.return_value = _rag_response(text=text, uri=uri)


def test_ask_parses_grounded_answer_from_chunk_and_trace(agent_config):
    events = [
        {
            "chunk": {
                "bytes": b"Summary:\nRoll back the latest deployment.",
            },
        },
        {
            "trace": {
                "orchestrationTrace": {
                    "observation": {
                        "knowledgeBaseLookupOutput": {
                            "retrievedReferences": [
                                {
                                    "content": {"text": "Use kubectl rollout undo to roll back."},
                                    "location": {
                                        "type": "S3",
                                        "s3Location": {"uri": "s3://kb/deployment_runbook.md"},
                                    },
                                }
                            ]
                        }
                    }
                }
            }
        },
    ]
    mock_client = MagicMock()
    mock_client.invoke_agent.return_value = _stream(events)

    client = BedrockAgentClient(agent_config, client=mock_client)
    result = client.ask("Deployment broke prod, what now?")

    assert result.grounded is True
    assert "Roll back" in result.answer
    assert len(result.citations) == 1
    assert result.citations[0].source_label == "deployment_runbook.md"
    assert result.session_id == "sess-agent-1"
    assert result.latency_ms >= 0

    call = mock_client.invoke_agent.call_args.kwargs
    assert call["agentId"] == "AGENT123"
    assert call["agentAliasId"] == "ALIAS456"
    assert call["inputText"] == "Deployment broke prod, what now?"
    assert call["sessionId"]


def test_ask_parses_attribution_citations(agent_config):
    events = [
        {
            "chunk": {
                "bytes": b"Check DB connection pool settings.",
                "attribution": {
                    "citations": [
                        {
                            "retrievedReferences": [
                                {
                                    "content": {"text": "Verify max_connections on RDS."},
                                    "location": {
                                        "s3Location": {"uri": "s3://kb/database_connectivity.md"},
                                    },
                                }
                            ]
                        }
                    ]
                },
            },
        },
    ]
    mock_client = MagicMock()
    mock_client.invoke_agent.return_value = _stream(events)

    result = BedrockAgentClient(agent_config, client=mock_client).ask("DB CPU high?")

    assert result.grounded is True
    assert result.citations[0].source_label == "database_connectivity.md"


def test_ask_handles_no_citations(agent_config):
    mock_client = MagicMock()
    mock_client.invoke_agent.return_value = _stream(
        [{"chunk": {"bytes": b"Sorry, I don't know."}}],
    )
    _mock_ungrounded_rag(mock_client)

    result = BedrockAgentClient(agent_config, client=mock_client).ask("unrelated question")

    assert result.grounded is False
    assert "don't know" in result.answer
    mock_client.retrieve_and_generate.assert_called_once()


def test_ask_backfills_from_kb_when_agent_ungrounded(agent_config):
    mock_client = MagicMock()
    mock_client.invoke_agent.return_value = _stream(
        [{"chunk": {"bytes": b"Generic answer without KB lookup."}}],
    )
    _mock_grounded_rag(
        mock_client,
        text="Priority:\nP2\n\nTriage plan:\n1. Check deploy logs and roll back.",
        uri="s3://kb/api_gateway_5xx.md",
    )

    result = BedrockAgentClient(agent_config, client=mock_client).ask(
        "API 5xx rate is above 2% on checkout — what should I check?",
    )

    assert result.grounded is True
    assert result.citations[0].source_label == "api_gateway_5xx.md"
    assert "Triage plan" in result.answer
    assert result.session_id == "sess-agent-1"


def test_ask_empty_response_gets_fallback_message(agent_config):
    mock_client = MagicMock()
    mock_client.invoke_agent.return_value = _stream([])
    _mock_ungrounded_rag(mock_client)

    result = BedrockAgentClient(agent_config, client=mock_client).ask("anything")

    assert result.grounded is False
    assert "could not find anything" in result.answer.lower()


def test_ask_passes_session_id(agent_config):
    mock_client = MagicMock()
    mock_client.invoke_agent.return_value = _stream(
        [{"chunk": {"bytes": b"ok"}}],
    )
    _mock_ungrounded_rag(mock_client)

    BedrockAgentClient(agent_config, client=mock_client).ask(
        "How do I roll back?", session_id="prev-sess",
    )

    assert mock_client.invoke_agent.call_args.kwargs["sessionId"] == "prev-sess"
    assert "sessionId" not in mock_client.retrieve_and_generate.call_args.kwargs
