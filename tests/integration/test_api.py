"""Integration tests for FastAPI webhook endpoint."""
import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api import create_app
from src.config import AppConfig
from src.services.tools.mock import MockToolManager


# Real Composio TriggerEvent format
VALID_WEBHOOK_PAYLOAD = {
    "trigger_slug": "GMAIL_NEW_GMAIL_MESSAGE",
    "payload": {
        "message_id": "msg-123",
        "thread_id": "thread-456",
        "subject": "PO-2024-001",
        "sender": "customer@example.com",
        "message_text": "Please find attached...",
        "attachment_list": [
            {"id": "att-789", "name": "po.pdf", "mimeType": "application/pdf"},
        ],
    },
}

PAYLOAD_NO_ATTACHMENT = {
    "payload": {
        "message_id": "msg-no-att",
        "subject": "Question about order",
        "sender": "user@test.com",
        "message_text": "Just a question",
    },
}

TEST_WEBHOOK_SECRET = "whsec_test_secret_for_unit_tests"


@pytest.fixture
def mock_workflow():
    workflow = MagicMock()
    workflow.invoke.return_value = {"final_status": "completed", "po_id": "PO-001"}
    return workflow


@pytest.fixture
def mock_tools():
    return MockToolManager(
        mock_message={
            "messageText": "Full email body from Gmail API",
            "subject": "PO-2024-001",
            "sender": "customer@example.com",
        },
    )


@pytest.fixture
def client(mock_workflow, mock_tools, monkeypatch):
    """Client without webhook secret (no verification)."""
    monkeypatch.delenv("COMPOSIO_WEBHOOK_SECRET", raising=False)
    with patch("src.api.WorkflowBuilder") as mock_builder_cls:
        mock_builder = MagicMock()
        mock_builder_cls.return_value = mock_builder
        mock_builder.build.return_value = mock_workflow
        mock_builder.tool_manager = mock_tools
        app = create_app(AppConfig(tool_manager="mock", composio_webhook_secret=None, _env_file=None))
    return TestClient(app)


@pytest.fixture
def secure_client(mock_workflow, mock_tools, monkeypatch):
    """Client with webhook secret (verification enabled)."""
    monkeypatch.delenv("COMPOSIO_WEBHOOK_SECRET", raising=False)
    with patch("src.api.WorkflowBuilder") as mock_builder_cls:
        mock_builder = MagicMock()
        mock_builder_cls.return_value = mock_builder
        mock_builder.build.return_value = mock_workflow
        mock_builder.tool_manager = mock_tools
        app = create_app(AppConfig(
            tool_manager="mock",
            composio_webhook_secret=TEST_WEBHOOK_SECRET,
            _env_file=None,
        ))
    return TestClient(app)


def _sign_payload(payload_dict: dict, secret: str) -> dict:
    """Generate Composio-style webhook signature headers."""
    body = json.dumps(payload_dict)
    msg_id = "msg_test123"
    timestamp = str(int(time.time()))
    to_sign = f"{msg_id}.{timestamp}.{body}"
    signature = hmac.new(
        secret.encode(), to_sign.encode(), hashlib.sha256
    ).hexdigest()
    return {
        "webhook-id": msg_id,
        "webhook-timestamp": timestamp,
        "webhook-signature": f"v1,{signature}",
    }


class TestHealthEndpoint:
    def test_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestWebhookEndpoint:
    def test_returns_202_with_message_id(self, client):
        response = client.post("/webhook/email", json=VALID_WEBHOOK_PAYLOAD)
        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "accepted"
        assert body["message_id"] == "msg-123"

    def test_invalid_payload_returns_422(self, client):
        response = client.post("/webhook/email", json={"bad": "data"})
        assert response.status_code == 422

    def test_missing_data_returns_422(self, client):
        response = client.post("/webhook/email", json={})
        assert response.status_code == 422


class TestWebhookVerification:
    def test_no_secret_configured_skips_verification(self, client):
        """When no secret is set, webhook accepts without signature headers."""
        response = client.post("/webhook/email", json=VALID_WEBHOOK_PAYLOAD)
        assert response.status_code == 202

    def test_missing_signature_returns_401(self, secure_client):
        """When secret is set but request has no signature headers, reject."""
        response = secure_client.post("/webhook/email", json=VALID_WEBHOOK_PAYLOAD)
        assert response.status_code == 401

    def test_invalid_signature_returns_401(self, secure_client):
        """When signature doesn't match, reject."""
        headers = {
            "webhook-id": "msg_fake",
            "webhook-timestamp": str(int(time.time())),
            "webhook-signature": "v1,invalidsignature",
        }
        response = secure_client.post(
            "/webhook/email", json=VALID_WEBHOOK_PAYLOAD, headers=headers
        )
        assert response.status_code == 401

    def test_valid_signature_passes(self, secure_client):
        """When signature is valid, accept the webhook."""
        headers = _sign_payload(VALID_WEBHOOK_PAYLOAD, TEST_WEBHOOK_SECRET)
        response = secure_client.post(
            "/webhook/email",
            content=json.dumps(VALID_WEBHOOK_PAYLOAD),
            headers={**headers, "content-type": "application/json"},
        )
        assert response.status_code == 202


class TestProcessEmail:
    def test_fetches_full_message(self, client, mock_tools):
        client.post("/webhook/email", json=VALID_WEBHOOK_PAYLOAD)
        message_calls = [c for c in mock_tools.all_calls if c["action"] == "get_email_message"]
        assert len(message_calls) == 1
        assert message_calls[0]["message_id"] == "msg-123"

    def test_fetches_attachment_when_present(self, client, mock_tools):
        client.post("/webhook/email", json=VALID_WEBHOOK_PAYLOAD)
        att_calls = [c for c in mock_tools.all_calls if c["action"] == "get_email_attachment"]
        assert len(att_calls) == 1
        assert att_calls[0]["message_id"] == "msg-123"
        assert att_calls[0]["attachment_id"] == "att-789"

    def test_skips_attachment_when_none(self, client, mock_tools):
        client.post("/webhook/email", json=PAYLOAD_NO_ATTACHMENT)
        att_calls = [c for c in mock_tools.all_calls if c["action"] == "get_email_attachment"]
        assert len(att_calls) == 0

    def test_invokes_workflow(self, client, mock_workflow):
        client.post("/webhook/email", json=VALID_WEBHOOK_PAYLOAD)
        mock_workflow.invoke.assert_called_once()
        call_args = mock_workflow.invoke.call_args[0][0]
        assert call_args["email_message_id"] == "msg-123"
        assert call_args["has_attachment"] is True
        assert call_args["thread_id"] == "thread-456"

    def test_workflow_receives_full_message_body(self, client, mock_workflow):
        client.post("/webhook/email", json=VALID_WEBHOOK_PAYLOAD)
        call_args = mock_workflow.invoke.call_args[0][0]
        # MockToolManager returns mock_message with "messageText", so process_email uses it
        assert call_args["email_body"] == "Full email body from Gmail API"

    def test_workflow_receives_empty_state_lists(self, client, mock_workflow):
        client.post("/webhook/email", json=VALID_WEBHOOK_PAYLOAD)
        call_args = mock_workflow.invoke.call_args[0][0]
        assert call_args["actions_log"] == []
        assert call_args["trajectory"] == []
