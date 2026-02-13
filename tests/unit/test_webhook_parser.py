"""Unit tests for Composio webhook payload parsing."""
import pytest
from pydantic import ValidationError

from src.core.webhook import (
    ComposioWebhookPayload,
    WebhookPayload,
    parse_composio_webhook,
)


VALID_PAYLOAD = {
    "log_id": "log_abc123",
    "timestamp": "2026-02-13T10:00:00Z",
    "type": "gmail_new_gmail_message",
    "data": {
        "messageId": "msg-123",
        "threadId": "thread-456",
        "subject": "PO-2024-001 Order",
        "sender": "customer@example.com",
        "snippet": "Please find attached our purchase order...",
        "attachments": [
            {"attachmentId": "att-789", "filename": "po.pdf"},
        ],
    },
}


class TestComposioWebhookPayloadValidation:
    def test_validates_correct_payload(self):
        payload = ComposioWebhookPayload(**VALID_PAYLOAD)
        assert payload.data.messageId == "msg-123"
        assert payload.log_id == "log_abc123"
        assert payload.type == "gmail_new_gmail_message"

    def test_rejects_missing_message_id(self):
        bad_payload = {
            "data": {
                "subject": "Test",
            }
        }
        with pytest.raises(ValidationError):
            ComposioWebhookPayload(**bad_payload)

    def test_rejects_missing_data(self):
        with pytest.raises(ValidationError):
            ComposioWebhookPayload()

    def test_optional_fields_default_gracefully(self):
        minimal_payload = {
            "data": {
                "messageId": "msg-minimal",
            }
        }
        payload = ComposioWebhookPayload(**minimal_payload)
        assert payload.data.messageId == "msg-minimal"
        assert payload.data.threadId is None
        assert payload.data.subject == ""
        assert payload.data.sender == ""
        assert payload.data.snippet == ""
        assert payload.data.attachments == []
        assert payload.log_id is None
        assert payload.timestamp is None
        assert payload.type is None

    def test_parses_attachments(self):
        payload = ComposioWebhookPayload(**VALID_PAYLOAD)
        assert len(payload.data.attachments) == 1
        assert payload.data.attachments[0].attachmentId == "att-789"
        assert payload.data.attachments[0].filename == "po.pdf"

    def test_multiple_attachments(self):
        multi = {
            "data": {
                "messageId": "msg-multi",
                "attachments": [
                    {"attachmentId": "att-1", "filename": "po1.pdf"},
                    {"attachmentId": "att-2", "filename": "po2.pdf"},
                    {"attachmentId": "att-3"},
                ],
            }
        }
        payload = ComposioWebhookPayload(**multi)
        assert len(payload.data.attachments) == 3
        assert payload.data.attachments[2].filename is None


class TestParseComposioWebhook:
    def test_converts_to_webhook_payload(self):
        composio_payload = ComposioWebhookPayload(**VALID_PAYLOAD)
        result = parse_composio_webhook(composio_payload)

        assert isinstance(result, WebhookPayload)
        assert result.message_id == "msg-123"
        assert result.subject == "PO-2024-001 Order"
        assert result.body == "Please find attached our purchase order..."
        assert result.sender == "customer@example.com"
        assert result.has_attachment is True
        assert result.attachment_ids == ["att-789"]
        assert result.thread_id == "thread-456"

    def test_no_attachments(self):
        no_att = {
            "data": {
                "messageId": "msg-no-att",
                "subject": "Question",
                "sender": "user@test.com",
                "snippet": "Just a question",
            }
        }
        composio_payload = ComposioWebhookPayload(**no_att)
        result = parse_composio_webhook(composio_payload)

        assert result.has_attachment is False
        assert result.attachment_ids == []

    def test_no_thread_id(self):
        no_thread = {
            "data": {
                "messageId": "msg-no-thread",
            }
        }
        composio_payload = ComposioWebhookPayload(**no_thread)
        result = parse_composio_webhook(composio_payload)

        assert result.thread_id is None

    def test_extracts_multiple_attachment_ids(self):
        multi = {
            "data": {
                "messageId": "msg-multi",
                "attachments": [
                    {"attachmentId": "att-1"},
                    {"attachmentId": "att-2"},
                ],
            }
        }
        composio_payload = ComposioWebhookPayload(**multi)
        result = parse_composio_webhook(composio_payload)

        assert result.attachment_ids == ["att-1", "att-2"]
        assert result.has_attachment is True
