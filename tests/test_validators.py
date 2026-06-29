"""Tests for shared question validation."""
from __future__ import annotations

import pytest

from app.errors import BedrockError
from app.validators import MAX_QUESTION_LEN, validate_question


def test_validate_accepts_normal_question():
    assert validate_question("  How do I fix auth?  ") == "How do I fix auth?"


def test_validate_rejects_empty():
    with pytest.raises(BedrockError) as exc:
        validate_question("   ")
    assert exc.value.code == "empty_question"


def test_validate_rejects_short():
    with pytest.raises(BedrockError) as exc:
        validate_question("ab")
    assert exc.value.code == "short_question"


def test_validate_rejects_oversize():
    with pytest.raises(BedrockError) as exc:
        validate_question("x" * (MAX_QUESTION_LEN + 1))
    assert exc.value.code == "oversize_question"


def test_validate_rejects_stopwords_only():
    with pytest.raises(BedrockError) as exc:
        validate_question("what is the")
    assert exc.value.code == "stopwords_only"


def test_validate_accepts_exact_max_length():
    q = "a" * MAX_QUESTION_LEN
    assert len(validate_question(q)) == MAX_QUESTION_LEN
