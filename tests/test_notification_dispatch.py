"""Tests for SNS/SES notification dispatch."""
from __future__ import annotations

import pytest

from app.services.notification_dispatch import (
    NotificationDispatchError,
    check_sms_account_ready,
    dispatch_sms,
    dispatch_whatsapp,
    sms_use_topic,
    sms_use_voice_v2,
    whatsapp_configured,
)


def test_sms_use_topic_defaults_false(monkeypatch):
    monkeypatch.delenv("PITER_SNS_SMS_USE_TOPIC", raising=False)
    assert sms_use_topic() is False


def test_sms_use_voice_v2_defaults_true(monkeypatch):
    monkeypatch.delenv("PITER_SMS_USE_VOICE_V2", raising=False)
    assert sms_use_voice_v2() is True


def test_dispatch_sms_uses_voice_v2_by_default(monkeypatch):
    monkeypatch.setenv("PITER_SMS_PREFLIGHT_CHECK", "false")
    calls: list[dict] = []

    class FakeVoiceV2:
        def send_text_message(self, **kwargs):
            calls.append(kwargs)
            return {"MessageId": "voice-v2-1"}

    def fake_client(name, region_name=None):
        if name == "pinpoint-sms-voice-v2":
            return FakeVoiceV2()
        raise AssertionError(f"unexpected client: {name}")

    monkeypatch.setattr("app.services.notification_dispatch.boto3.client", fake_client)

    result = dispatch_sms("+15551234567", "hello")
    assert result["sent"] is True
    assert result["route"] == "voice_v2"
    assert calls[0]["DestinationPhoneNumber"] == "+15551234567"
    assert calls[0]["MessageType"] == "TRANSACTIONAL"


def test_dispatch_sms_uses_direct_phone_by_default(monkeypatch):
    monkeypatch.delenv("PITER_SNS_TOPIC_ARN", raising=False)
    monkeypatch.setenv("PITER_SMS_PREFLIGHT_CHECK", "false")
    monkeypatch.setenv("PITER_SMS_USE_VOICE_V2", "false")
    monkeypatch.delenv("PITER_SNS_SMS_USE_TOPIC", raising=False)

    calls: list[dict] = []

    class FakeSns:
        def publish(self, **kwargs):
            calls.append(kwargs)
            return {"MessageId": "sms-123"}

    monkeypatch.setattr(
        "app.services.notification_dispatch.boto3.client",
        lambda _name, region_name=None: FakeSns(),
    )

    result = dispatch_sms("+15551234567", "hello")
    assert result["sent"] is True
    assert result["route"] == "direct"
    assert calls[0]["PhoneNumber"] == "+15551234567"
    assert "TopicArn" not in calls[0]
    assert "Subject" not in calls[0]


def test_dispatch_sms_can_use_topic_when_enabled(monkeypatch):
    monkeypatch.setenv("PITER_SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123:topic")
    monkeypatch.setenv("PITER_SNS_SMS_USE_TOPIC", "true")
    monkeypatch.setenv("PITER_SMS_USE_VOICE_V2", "false")
    monkeypatch.setenv("PITER_SMS_PREFLIGHT_CHECK", "false")

    calls: list[dict] = []

    class FakeSns:
        def get_sms_attributes(self, attributes=None):
            return {"attributes": {"MonthlySpendLimit": "10", "DefaultSMSType": "Transactional"}}

        def get_paginator(self, _name):
            class Paginator:
                def paginate(self, TopicArn=None):
                    yield {
                        "Subscriptions": [
                            {
                                "Protocol": "sms",
                                "Endpoint": "+15551234567",
                                "SubscriptionArn": "arn:aws:sns:us-east-1:123:topic:abc",
                            }
                        ]
                    }

            return Paginator()

        def publish(self, **kwargs):
            calls.append(kwargs)
            return {"MessageId": "sms-topic-1"}

    monkeypatch.setattr(
        "app.services.notification_dispatch.boto3.client",
        lambda _name, region_name=None: FakeSns(),
    )

    result = dispatch_sms("+15551234567", "hello")
    assert result["route"] == "topic"
    assert calls[0]["TopicArn"] == "arn:aws:sns:us-east-1:123:topic"
    assert "Subject" not in calls[0]


def test_dispatch_sms_preflight_blocks_when_account_not_ready(monkeypatch):
    monkeypatch.setenv("PITER_SMS_PREFLIGHT_CHECK", "true")
    monkeypatch.delenv("PITER_SNS_TOPIC_ARN", raising=False)

    class FakeVoiceV2:
        def describe_account_attributes(self):
            raise __import__("botocore.exceptions", fromlist=["ClientError"]).ClientError(
                {"Error": {"Code": "UserError", "Message": "PinpointSmsVoiceV2 subscription required"}},
                "DescribeAccountAttributes",
            )

    class FakeSns:
        def get_sms_attributes(self, attributes=None):
            raise __import__("botocore.exceptions", fromlist=["ClientError"]).ClientError(
                {"Error": {"Code": "UserError", "Message": "PinpointSmsVoiceV2 subscription required"}},
                "GetSMSAttributes",
            )

    def fake_client(name, region_name=None):
        if name == "pinpoint-sms-voice-v2":
            return FakeVoiceV2()
        return FakeSns()

    monkeypatch.setattr("app.services.notification_dispatch.boto3.client", fake_client)

    with pytest.raises(NotificationDispatchError) as exc:
        dispatch_sms("+15551234567", "hello")
    assert exc.value.code == "sms_service_not_enabled"


def test_dispatch_sms_stays_direct_when_topic_subscriber_confirmed(monkeypatch):
    monkeypatch.setenv("PITER_SMS_PREFLIGHT_CHECK", "true")
    monkeypatch.setenv("PITER_SMS_USE_VOICE_V2", "false")
    monkeypatch.delenv("PITER_SNS_SMS_USE_TOPIC", raising=False)
    monkeypatch.setenv(
        "PITER_SNS_TOPIC_ARN",
        "arn:aws:sns:us-east-1:${AWS_ACCOUNT_ID}:piter-aiops-escalation",
    )
    calls: list[str] = []

    class FakeSns:
        def get_sms_attributes(self, attributes=None):
            return {"attributes": {"MonthlySpendLimit": "10", "DefaultSMSType": "Transactional"}}

        def get_paginator(self, _name):
            class Paginator:
                def paginate(self, TopicArn=None):
                    yield {
                        "Subscriptions": [
                            {
                                "Protocol": "sms",
                                "Endpoint": "+15551234567",
                                "SubscriptionArn": (
                                    "arn:aws:sns:us-east-1:${AWS_ACCOUNT_ID}:piter-aiops-escalation:abc"
                                ),
                            }
                        ]
                    }

            return Paginator()

        def publish(self, **kwargs):
            calls.append(kwargs.get("TopicArn") or kwargs.get("PhoneNumber", ""))
            return {"MessageId": "sms-direct-2"}

    monkeypatch.setattr(
        "app.services.notification_dispatch.boto3.client",
        lambda _name, region_name=None: FakeSns(),
    )

    result = dispatch_sms("+15551234567", "hello")
    assert result["sent"] is True
    assert result["route"] == "direct"
    assert calls[0] == "+15551234567"


def test_topic_subscription_alone_is_not_delivery_ready(monkeypatch):
    monkeypatch.setenv("PITER_SMS_USE_VOICE_V2", "false")
    monkeypatch.setenv(
        "PITER_SNS_TOPIC_ARN",
        "arn:aws:sns:us-east-1:${AWS_ACCOUNT_ID}:piter-aiops-escalation",
    )

    class FakeSns:
        def get_sms_attributes(self, attributes=None):
            raise __import__("botocore.exceptions", fromlist=["ClientError"]).ClientError(
                {"Error": {"Code": "UserError", "Message": "PinpointSmsVoiceV2 subscription required"}},
                "GetSMSAttributes",
            )

        def get_paginator(self, _name):
            class Paginator:
                def paginate(self, TopicArn=None):
                    yield {
                        "Subscriptions": [
                            {
                                "Protocol": "sms",
                                "Endpoint": "+15551234567",
                                "SubscriptionArn": (
                                    "arn:aws:sns:us-east-1:${AWS_ACCOUNT_ID}:piter-aiops-escalation:abc"
                                ),
                            }
                        ]
                    }

            return Paginator()

    monkeypatch.setattr(
        "app.services.notification_dispatch.boto3.client",
        lambda _name, region_name=None: FakeSns(),
    )

    status = check_sms_account_ready(phone="+15551234567")
    assert status["ready"] is False
    assert status["reason"] == "sms_service_not_enabled"
    assert status.get("topic_subscribers") == 1


def test_check_sms_account_ready_ok(monkeypatch):
    monkeypatch.delenv("PITER_SNS_TOPIC_ARN", raising=False)

    class FakeVoiceV2:
        def describe_account_attributes(self):
            return {"AccountAttributes": [{"Name": "ACCOUNT_TIER", "Value": "SANDBOX"}]}

    class FakeSns:
        def get_sms_attributes(self, attributes=None):
            return {"attributes": {"MonthlySpendLimit": "10", "DefaultSMSType": "Transactional"}}

    def fake_client(name, region_name=None):
        if name == "pinpoint-sms-voice-v2":
            return FakeVoiceV2()
        return FakeSns()

    monkeypatch.setattr("app.services.notification_dispatch.boto3.client", fake_client)
    status = check_sms_account_ready()
    assert status["ready"] is True
    assert status.get("route") == "voice_v2"


def test_whatsapp_configured_requires_api_key(monkeypatch):
    monkeypatch.setenv("PITER_DEMO_SMS_RECIPIENT", "+15551234567")
    monkeypatch.delenv("PITER_WHATSAPP_API_KEY", raising=False)
    assert whatsapp_configured() is False
    monkeypatch.setenv("PITER_WHATSAPP_API_KEY", "abc123")
    assert whatsapp_configured() is True


def test_dispatch_whatsapp_callmebot(monkeypatch):
    monkeypatch.setenv("PITER_WHATSAPP_API_KEY", "test-key")
    monkeypatch.setenv("PITER_DEMO_SMS_RECIPIENT", "+15551234567")
    urls: list[str] = []

    class FakeResponse:
        status = 200

        def read(self):
            return b"OK"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout=15):
        urls.append(getattr(request, "full_url", str(request)))
        return FakeResponse()

    monkeypatch.setattr("app.services.notification_dispatch.urllib.request.urlopen", fake_urlopen)

    result = dispatch_whatsapp("+15551234567", "P1 bet-service")
    assert result["sent"] is True
    assert result["provider"] == "callmebot"
    assert "callmebot.com" in urls[0]
    assert "test-key" in urls[0]


def test_dispatch_sms_falls_back_to_whatsapp_when_sms_blocked(monkeypatch):
    monkeypatch.setenv("PITER_SMS_PREFLIGHT_CHECK", "true")
    monkeypatch.delenv("PITER_SNS_TOPIC_ARN", raising=False)
    monkeypatch.setenv("PITER_WHATSAPP_API_KEY", "wa-key")
    monkeypatch.setenv("PITER_DEMO_SMS_RECIPIENT", "+15551234567")

    class FakeVoiceV2:
        def describe_account_attributes(self):
            raise __import__("botocore.exceptions", fromlist=["ClientError"]).ClientError(
                {"Error": {"Code": "UserError", "Message": "PinpointSmsVoiceV2 subscription required"}},
                "DescribeAccountAttributes",
            )

    class FakeSns:
        def get_sms_attributes(self, attributes=None):
            raise __import__("botocore.exceptions", fromlist=["ClientError"]).ClientError(
                {"Error": {"Code": "UserError", "Message": "PinpointSmsVoiceV2 subscription required"}},
                "GetSMSAttributes",
            )

    class FakeResponse:
        status = 200

        def read(self):
            return b"OK"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_client(name, region_name=None):
        if name == "pinpoint-sms-voice-v2":
            return FakeVoiceV2()
        return FakeSns()

    monkeypatch.setattr(
        "app.services.notification_dispatch.boto3.client",
        fake_client,
    )
    monkeypatch.setattr(
        "app.services.notification_dispatch.urllib.request.urlopen",
        lambda url, timeout=15: FakeResponse(),
    )

    result = dispatch_sms("+15551234567", "hello")
    assert result["sent"] is True
    assert result.get("fallback_from") == "sms"
    assert result["channel"] == "whatsapp"
