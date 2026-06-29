"""Unit tests for BedrockRagClient using botocore Stubber — no real AWS calls."""
from __future__ import annotations

from unittest.mock import MagicMock

import boto3
import pytest
from botocore.stub import Stubber

from app.bedrock_client import BedrockRagClient, RAG_GENERATION_PROMPT
from app.config import Config
from app.errors import BedrockError
from app.validators import MAX_QUESTION_LEN


@pytest.fixture
def config():
    return Config(
        AWS_REGION="us-east-1",
        BEDROCK_KB_ID="KBTEST1234",
        BEDROCK_MODEL_ARN="arn:aws:bedrock:us-east-1::foundation-model/test",
        BEDROCK_NUM_RESULTS=5,
        SECRET_KEY="x",
        FLASK_ENV="testing",
    )


def _make_client_with_stub(config: Config):
    raw = boto3.client("bedrock-agent-runtime", region_name=config.AWS_REGION)
    stub = Stubber(raw)
    client = BedrockRagClient(config, client=raw)
    return client, stub


def test_ask_parses_grounded_answer(config):
    client, stub = _make_client_with_stub(config)
    stub.add_response(
        "retrieve_and_generate",
        {
            "output": {"text": "Roll back the latest deployment, then verify health."},
            "citations": [
                {
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
            ],
            "sessionId": "session-abc",
        },
    )

    with stub:
        result = client.ask("Deployment broke prod, what now?")

    assert result.grounded is True
    assert "Roll back" in result.answer
    assert len(result.citations) == 1
    assert result.citations[0].source_uri == "s3://kb/deployment_runbook.md"
    assert result.citations[0].source_label == "deployment_runbook.md"
    assert result.citations[0].index == 1
    assert result.matched_runbook == "deployment_runbook.md"
    assert result.latency_ms >= 0
    assert result.session_id == "session-abc"


def test_ask_handles_no_citations(config):
    client, stub = _make_client_with_stub(config)
    stub.add_response(
        "retrieve_and_generate",
        {"output": {"text": "Sorry, I don't know."}, "citations": [], "sessionId": "sess-x"},
    )
    with stub:
        result = client.ask("unrelated question")
    assert result.grounded is False
    assert result.citations == []


def test_ask_rejects_empty_question(config):
    client, _ = _make_client_with_stub(config)
    with pytest.raises(BedrockError) as exc:
        client.ask("   ")
    assert exc.value.code == "empty_question"


def test_ask_rejects_oversize_question(config):
    client, _ = _make_client_with_stub(config)
    with pytest.raises(BedrockError) as exc:
        client.ask("x" * (MAX_QUESTION_LEN + 1))
    assert exc.value.code == "oversize_question"


def test_ask_rejects_short_question(config):
    client, _ = _make_client_with_stub(config)
    with pytest.raises(BedrockError) as exc:
        client.ask("ab")
    assert exc.value.code == "short_question"


def test_ask_rejects_stopwords_only(config):
    client, _ = _make_client_with_stub(config)
    with pytest.raises(BedrockError) as exc:
        client.ask("what is the")
    assert exc.value.code == "stopwords_only"


def test_ask_translates_throttling_error(config):
    client, stub = _make_client_with_stub(config)
    stub.add_client_error(
        "retrieve_and_generate",
        service_error_code="ThrottlingException",
        service_message="Rate exceeded",
        http_status_code=429,
    )
    with stub:
        with pytest.raises(BedrockError) as exc:
            client.ask("anything")
    assert exc.value.code == "ThrottlingException"
    assert "throttling" in exc.value.user_message.lower()


def test_ask_translates_access_denied(config):
    client, stub = _make_client_with_stub(config)
    stub.add_client_error(
        "retrieve_and_generate",
        service_error_code="AccessDeniedException",
        service_message="forbidden",
        http_status_code=403,
    )
    with stub:
        with pytest.raises(BedrockError) as exc:
            client.ask("anything")
    assert exc.value.code == "AccessDeniedException"


def test_ask_translates_resource_not_found(config):
    client, stub = _make_client_with_stub(config)
    stub.add_client_error(
        "retrieve_and_generate",
        service_error_code="ResourceNotFoundException",
        service_message="kb missing",
        http_status_code=404,
    )
    with stub, pytest.raises(BedrockError) as exc:
        client.ask("anything")
    assert exc.value.code == "ResourceNotFoundException"
    assert "Knowledge Base" in exc.value.user_message


def test_ask_translates_validation_error(config):
    client, stub = _make_client_with_stub(config)
    stub.add_client_error(
        "retrieve_and_generate",
        service_error_code="ValidationException",
        service_message="bad request",
        http_status_code=400,
    )
    with stub, pytest.raises(BedrockError) as exc:
        client.ask("anything")
    assert exc.value.code == "ValidationException"


def test_ask_handles_unknown_error_code(config):
    client, stub = _make_client_with_stub(config)
    stub.add_client_error(
        "retrieve_and_generate",
        service_error_code="SomeNewException",
        service_message="weird",
        http_status_code=500,
    )
    with stub, pytest.raises(BedrockError) as exc:
        client.ask("anything")
    assert exc.value.code == "SomeNewException"
    assert exc.value.user_message  # friendly fallback present


def test_ask_dedupes_empty_snippet_refs(config):
    """Citations with empty snippet text should be filtered out."""
    client, stub = _make_client_with_stub(config)
    stub.add_response(
        "retrieve_and_generate",
        {
            "output": {"text": "Real answer."},
            "citations": [
                {
                    "retrievedReferences": [
                        {"content": {"text": "   "}, "location": {"type": "S3", "s3Location": {"uri": "s3://kb/x.md"}}},
                        {"content": {"text": "Good chunk."}, "location": {"type": "S3", "s3Location": {"uri": "s3://kb/y.md"}}},
                    ]
                }
            ],
            "sessionId": "ss",
        },
    )
    with stub:
        result = client.ask("anything")
    assert len(result.citations) == 1
    assert result.citations[0].snippet == "Good chunk."


def test_ask_handles_missing_source_uri(config):
    """Bedrock can return references with no S3 location — render snippet only."""
    client, stub = _make_client_with_stub(config)
    stub.add_response(
        "retrieve_and_generate",
        {
            "output": {"text": "Answer."},
            "citations": [
                {"retrievedReferences": [{"content": {"text": "loose chunk"}, "location": {"type": "S3"}}]},
            ],
            "sessionId": "ss",
        },
    )
    with stub:
        result = client.ask("anything")
    assert result.grounded is True
    assert result.citations[0].source_uri is None


def test_ask_handles_multi_citation_groups(config):
    """A single output can include multiple citation groups, each with several refs."""
    client, stub = _make_client_with_stub(config)
    stub.add_response(
        "retrieve_and_generate",
        {
            "output": {"text": "Combined answer."},
            "citations": [
                {"retrievedReferences": [
                    {"content": {"text": "from a"}, "location": {"type": "S3", "s3Location": {"uri": "s3://kb/a"}}},
                    {"content": {"text": "from b"}, "location": {"type": "S3", "s3Location": {"uri": "s3://kb/b"}}},
                ]},
                {"retrievedReferences": [
                    {"content": {"text": "from c"}, "location": {"type": "S3", "s3Location": {"uri": "s3://kb/c"}}},
                ]},
            ],
            "sessionId": "ss",
        },
    )
    with stub:
        result = client.ask("anything")
    assert [c.source_uri for c in result.citations] == ["s3://kb/a", "s3://kb/b", "s3://kb/c"]


def test_ask_default_message_when_no_answer_and_no_citations(config):
    """If KB returns truly nothing, we still produce a friendly answer string."""
    client, stub = _make_client_with_stub(config)
    stub.add_response(
        "retrieve_and_generate",
        {"output": {"text": ""}, "citations": [], "sessionId": "ss"},
    )
    with stub:
        result = client.ask("anything")
    assert result.grounded is False
    assert "could not find" in result.answer.lower()


def test_ask_dedupes_duplicate_citations(config):
    client, stub = _make_client_with_stub(config)
    stub.add_response(
        "retrieve_and_generate",
        {
            "output": {"text": "Answer."},
            "citations": [
                {
                    "retrievedReferences": [
                        {
                            "content": {"text": "same chunk text here"},
                            "location": {"type": "S3", "s3Location": {"uri": "s3://kb/a.md"}},
                        },
                        {
                            "content": {"text": "same chunk text here"},
                            "location": {"type": "S3", "s3Location": {"uri": "s3://kb/a.md"}},
                        },
                    ]
                }
            ],
            "sessionId": "ss",
        },
    )
    with stub:
        result = client.ask("anything valid here")
    assert len(result.citations) == 1


def test_to_dict_shape(config):
    """RagAnswer.to_dict is the contract the future MCP tool wrapper will consume."""
    client, stub = _make_client_with_stub(config)
    stub.add_response(
        "retrieve_and_generate",
        {
            "output": {"text": "ans"},
            "citations": [{"retrievedReferences": [
                {"content": {"text": "snip"}, "location": {"type": "S3", "s3Location": {"uri": "s3://k/a.md"}}},
            ]}],
            "sessionId": "abc",
        },
    )
    with stub:
        d = client.ask("valid question here").to_dict()
    assert set(d.keys()) == {
        "answer",
        "answer_sections",
        "piter_sections",
        "citations",
        "session_id",
        "grounded",
        "latency_ms",
        "matched_runbook",
        "mode",
        "fallback_used",
    }
    assert d["citations"][0]["source_label"] == "a.md"
    assert d["citations"][0]["index"] == 1
    assert "preview" in d["citations"][0]
    assert "steps" in d["answer_sections"]


def test_ask_sends_custom_generation_prompt(config):
    mock_client = MagicMock()
    mock_client.retrieve_and_generate.return_value = {
        "output": {"text": "Check recent deployments first."},
        "citations": [],
        "sessionId": "sess-gen",
    }
    client = BedrockRagClient(config, client=mock_client)
    client.ask("Users cannot log in after a deployment")

    kwargs = mock_client.retrieve_and_generate.call_args.kwargs
    kb_cfg = kwargs["retrieveAndGenerateConfiguration"]["knowledgeBaseConfiguration"]
    gen_cfg = kb_cfg["generationConfiguration"]
    assert gen_cfg["promptTemplate"]["textPromptTemplate"] == RAG_GENERATION_PROMPT
    assert gen_cfg["inferenceConfig"]["textInferenceConfig"]["temperature"] == 0.0
    assert "GlobalDataSource" in gen_cfg["inferenceConfig"]["textInferenceConfig"]["stopSequences"]
