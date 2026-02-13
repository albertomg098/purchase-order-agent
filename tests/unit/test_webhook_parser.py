"""Unit tests for Composio webhook payload parsing.

Tests use the real Composio TriggerEvent format:
- Envelope: trigger_slug, payload (dict with Gmail data)
- Gmail fields: message_id, subject, sender, message_text, thread_id, attachment_list
"""
import pytest
from pydantic import ValidationError

from src.core.webhook import (
    ComposioWebhookPayload,
    WebhookPayload,
    parse_composio_webhook,
)


# Real Composio V3 webhook format: metadata + data envelope
VALID_PAYLOAD = {
    "metadata": {
        "trigger_slug": "GMAIL_NEW_GMAIL_MESSAGE",
    },
    "data": {
        "message_id": "msg-123",
        "thread_id": "thread-456",
        "subject": "PO-2024-001 Order",
        "sender": "customer@example.com",
        "message_text": "Please find attached our purchase order...",
        "attachment_list": [
            {"attachmentId": "att-789", "filename": "po.pdf", "mimeType": "application/pdf"},
        ],
    },
}


class TestComposioWebhookPayloadValidation:
    def test_validates_correct_payload(self):
        payload = ComposioWebhookPayload(**VALID_PAYLOAD)
        assert payload.data.message_id == "msg-123"
        assert payload.metadata.trigger_slug == "GMAIL_NEW_GMAIL_MESSAGE"

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
                "message_id": "msg-minimal",
            }
        }
        payload = ComposioWebhookPayload(**minimal_payload)
        assert payload.data.message_id == "msg-minimal"
        assert payload.data.thread_id is None
        assert payload.data.subject == ""
        assert payload.data.sender == ""
        assert payload.data.message_text == ""
        assert payload.data.attachment_list == []
        assert payload.metadata is None

    def test_parses_attachments(self):
        payload = ComposioWebhookPayload(**VALID_PAYLOAD)
        assert len(payload.data.attachment_list) == 1
        assert payload.data.attachment_list[0].attachmentId == "att-789"
        assert payload.data.attachment_list[0].filename == "po.pdf"

    def test_multiple_attachments(self):
        multi = {
            "data": {
                "message_id": "msg-multi",
                "attachment_list": [
                    {"attachmentId": "att-1", "filename": "po1.pdf", "mimeType": "application/pdf"},
                    {"attachmentId": "att-2", "filename": "po2.pdf", "mimeType": "application/pdf"},
                    {"attachmentId": "att-3"},
                ],
            }
        }
        payload = ComposioWebhookPayload(**multi)
        assert len(payload.data.attachment_list) == 3
        assert payload.data.attachment_list[2].filename is None


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
                "message_id": "msg-no-att",
                "subject": "Question",
                "sender": "user@test.com",
                "message_text": "Just a question",
            }
        }
        composio_payload = ComposioWebhookPayload(**no_att)
        result = parse_composio_webhook(composio_payload)

        assert result.has_attachment is False
        assert result.attachment_ids == []

    def test_no_thread_id(self):
        no_thread = {
            "data": {
                "message_id": "msg-no-thread",
            }
        }
        composio_payload = ComposioWebhookPayload(**no_thread)
        result = parse_composio_webhook(composio_payload)

        assert result.thread_id is None

    def test_extracts_multiple_attachment_ids(self):
        multi = {
            "data": {
                "message_id": "msg-multi",
                "attachment_list": [
                    {"attachmentId": "att-1"},
                    {"attachmentId": "att-2"},
                ],
            }
        }
        composio_payload = ComposioWebhookPayload(**multi)
        result = parse_composio_webhook(composio_payload)

        assert result.attachment_ids == ["att-1", "att-2"]
        assert result.has_attachment is True
