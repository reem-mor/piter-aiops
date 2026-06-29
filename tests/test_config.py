"""Config edge cases: missing env vars, type coercion, defaults."""
import os
import pytest

from app.config import Config, ConfigError


REQUIRED = ["AWS_REGION", "BEDROCK_KB_ID", "BEDROCK_MODEL_ARN", "FLASK_SECRET_KEY"]


@pytest.fixture
def env(monkeypatch):
    for key in REQUIRED + [
        "BEDROCK_NUM_RESULTS",
        "FLASK_ENV",
        "RAG_BACKEND",
        "BEDROCK_AGENT_ID",
        "BEDROCK_AGENT_ALIAS_ID",
        "PITER_AWS_REGION",
        "PITER_BEDROCK_KB_ID",
        "PITER_BEDROCK_MODEL_ARN",
        "PITER_FLASK_SECRET_KEY",
        "PITER_BEDROCK_NUM_RESULTS",
        "PITER_RAG_BACKEND",
        "PITER_BEDROCK_AGENT_ID",
        "PITER_BEDROCK_AGENT_ALIAS_ID",
        "PITER_MOCK_MODE",
        "PITER_USE_BEDROCK",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("BEDROCK_KB_ID", "kb-1")
    monkeypatch.setenv("BEDROCK_MODEL_ARN", "arn:aws:bedrock:::foundation-model/x")
    monkeypatch.setenv("FLASK_SECRET_KEY", "secret")
    monkeypatch.setenv("RAG_BACKEND", "agent")
    monkeypatch.setenv("BEDROCK_AGENT_ID", "agent-1")
    monkeypatch.setenv("BEDROCK_AGENT_ALIAS_ID", "alias-1")
    return monkeypatch


def test_loads_when_all_required_present(env):
    cfg = Config.from_env()
    assert cfg.AWS_REGION == "us-east-1"
    assert cfg.BEDROCK_NUM_RESULTS == 5  # default
    assert cfg.FLASK_ENV == "production"  # default
    assert cfg.RAG_BACKEND == "agent"
    assert cfg.BEDROCK_AGENT_ID == "agent-1"


def test_retrieve_and_generate_backend_skips_agent_ids(env):
    env.setenv("RAG_BACKEND", "retrieve_and_generate")
    env.delenv("BEDROCK_AGENT_ID")
    env.delenv("BEDROCK_AGENT_ALIAS_ID")
    cfg = Config.from_env()
    assert cfg.RAG_BACKEND == "retrieve_and_generate"
    assert cfg.BEDROCK_AGENT_ID == ""


def test_agent_backend_requires_agent_ids(env):
    env.delenv("BEDROCK_AGENT_ID")
    with pytest.raises(ConfigError):
        Config.from_env()


def test_invalid_rag_backend_raises(env):
    env.setenv("RAG_BACKEND", "invalid")
    with pytest.raises(ConfigError):
        Config.from_env()


def test_num_results_overridable(env):
    env.setenv("BEDROCK_NUM_RESULTS", "10")
    assert Config.from_env().BEDROCK_NUM_RESULTS == 10


@pytest.mark.parametrize("var", REQUIRED)
def test_missing_required_var_raises_configerror(env, var):
    env.delenv(var)
    with pytest.raises(ConfigError) as exc:
        Config.from_env()
    assert var in str(exc.value)


def test_blank_required_var_raises_configerror(env):
    env.setenv("BEDROCK_KB_ID", "   ")
    with pytest.raises(ConfigError):
        Config.from_env()


def test_num_results_invalid_raises(env):
    env.setenv("BEDROCK_NUM_RESULTS", "not-a-number")
    with pytest.raises((ValueError, ConfigError)):
        Config.from_env()
