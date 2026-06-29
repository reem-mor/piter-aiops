"""Tests for chat intent guard."""
from app.services.chat_intent import small_talk_reply


def test_greeting_returns_capability_reply():
    reply = small_talk_reply("hey")
    assert reply is not None
    assert "PITER Ops" in reply


def test_help_returns_capability_reply():
    reply = small_talk_reply("what can you do?")
    assert reply is not None


def test_incident_question_not_small_talk():
    assert small_talk_reply("What was the last deployment for auth-service?") is None
