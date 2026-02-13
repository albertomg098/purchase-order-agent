"""Unit tests for ComposioToolManager with mocked Composio client."""
import base64
from unittest.mock import MagicMock, patch

import pytest

from src.services.tools.composio import ComposioToolManager
from src.services.tools.base import ToolManager


class TestComposioToolManagerConstructor:
    @patch("src.services.tools.composio.Composio")
    def test_creates_composio_client_with_api_key(self, mock_composio_cls):
        ComposioToolManager(api_key="test-key")
        mock_composio_cls.assert_called_once_with(
            api_key="test-key",
            toolkit_versions={},
        )

    @patch("src.services.tools.composio.Composio")
    def test_passes_toolkit_versions(self, mock_composio_cls):
        versions = {"gmail": "20251027_00", "googlesheets": "20251027_00"}
        ComposioToolManager(api_key="test-key", toolkit_versions=versions)
        mock_composio_cls.assert_called_once_with(
            api_key="test-key",
            toolkit_versions=versions,
        )

    @patch("src.services.tools.composio.Composio")
    def test_default_user_id_is_default(self, mock_composio_cls):
        mgr = ComposioToolManager(api_key="test-key")
        assert mgr._user_id == "default"

    @patch("src.services.tools.composio.Composio")
    def test_custom_user_id(self, mock_composio_cls):
        mgr = ComposioToolManager(api_key="test-key", user_id="custom-entity")
        assert mgr._user_id == "custom-entity"

    @patch("src.services.tools.composio.Composio")
    def test_implements_tool_manager_abc(self, mock_composio_cls):
        mgr = ComposioToolManager(api_key="test-key")
        assert isinstance(mgr, ToolManager)


class TestSendEmail:
    @patch("src.services.tools.composio.Composio")
    def test_calls_gmail_send_email(self, mock_composio_cls):
        mock_client = MagicMock()
        mock_composio_cls.return_value = mock_client
        mock_client.tools.execute.return_value = {"id": "msg-123"}

        mgr = ComposioToolManager(api_key="test-key")
        result = mgr.send_email(to="user@example.com", subject="Test", body="Hello")

        mock_client.tools.execute.assert_called_once_with(
            "GMAIL_SEND_EMAIL",
            user_id="default",
            arguments={
                "recipient_email": "user@example.com",
                "subject": "Test",
                "body": "Hello",
                "is_html": False,
            },
        )
        assert result["status"] == "ok"

    @patch("src.services.tools.composio.Composio")
    def test_passes_thread_id_when_provided(self, mock_composio_cls):
        mock_client = MagicMock()
        mock_composio_cls.return_value = mock_client
        mock_client.tools.execute.return_value = {"id": "msg-123"}

        mgr = ComposioToolManager(api_key="test-key")
        mgr.send_email(to="user@example.com", subject="Re: Test", body="Reply", thread_id="thread-456")

        call_args = mock_client.tools.execute.call_args
        assert call_args[1]["arguments"]["thread_id"] == "thread-456"

    @patch("src.services.tools.composio.Composio")
    def test_omits_thread_id_when_none(self, mock_composio_cls):
        mock_client = MagicMock()
        mock_composio_cls.return_value = mock_client
        mock_client.tools.execute.return_value = {"id": "msg-123"}

        mgr = ComposioToolManager(api_key="test-key")
        mgr.send_email(to="user@example.com", subject="Test", body="Hello")

        call_args = mock_client.tools.execute.call_args
        assert "thread_id" not in call_args[1]["arguments"]

    @patch("src.services.tools.composio.Composio")
    def test_uses_custom_user_id(self, mock_composio_cls):
        mock_client = MagicMock()
        mock_composio_cls.return_value = mock_client
        mock_client.tools.execute.return_value = {"id": "msg-123"}

        mgr = ComposioToolManager(api_key="test-key", user_id="entity-abc")
        mgr.send_email(to="user@example.com", subject="Test", body="Hello")

        call_args = mock_client.tools.execute.call_args
        assert call_args[1]["user_id"] == "entity-abc"


class TestAppendSheetRow:
    @patch("src.services.tools.composio.Composio")
    def test_calls_googlesheets_batch_update(self, mock_composio_cls):
        mock_client = MagicMock()
        mock_composio_cls.return_value = mock_client
        mock_client.tools.execute.return_value = {"updatedRows": 1}

        mgr = ComposioToolManager(api_key="test-key")
        result = mgr.append_sheet_row(spreadsheet_id="sheet-123", values=["PO-001", "Acme"])

        mock_client.tools.execute.assert_called_once_with(
            "GOOGLESHEETS_BATCH_UPDATE",
            user_id="default",
            arguments={
                "spreadsheet_id": "sheet-123",
                "sheet_name": "Sheet1",
                "values": [["PO-001", "Acme"]],
            },
        )
        assert result["status"] == "ok"

    @patch("src.services.tools.composio.Composio")
    def test_uses_custom_sheet_name(self, mock_composio_cls):
        mock_client = MagicMock()
        mock_composio_cls.return_value = mock_client
        mock_client.tools.execute.return_value = {"updatedRows": 1}

        mgr = ComposioToolManager(api_key="test-key", sheet_name="PO Tracking")
        mgr.append_sheet_row(spreadsheet_id="sheet-123", values=["PO-001"])

        call_args = mock_client.tools.execute.call_args
        assert call_args[1]["arguments"]["sheet_name"] == "PO Tracking"


class TestGetEmailAttachment:
    @patch("src.services.tools.composio.Composio")
    def test_calls_gmail_get_attachment_and_decodes_base64(self, mock_composio_cls):
        mock_client = MagicMock()
        mock_composio_cls.return_value = mock_client

        raw_bytes = b"PDF content here"
        encoded = base64.b64encode(raw_bytes).decode()
        mock_client.tools.execute.return_value = {"data": encoded}

        mgr = ComposioToolManager(api_key="test-key")
        result = mgr.get_email_attachment(message_id="msg-123", attachment_id="att-456")

        mock_client.tools.execute.assert_called_once_with(
            "GMAIL_GET_ATTACHMENT",
            user_id="default",
            arguments={
                "message_id": "msg-123",
                "attachment_id": "att-456",
                "user_id": "me",
            },
        )
        assert result == raw_bytes


class TestGetEmailMessage:
    @patch("src.services.tools.composio.Composio")
    def test_calls_gmail_fetch_message(self, mock_composio_cls):
        mock_client = MagicMock()
        mock_composio_cls.return_value = mock_client
        mock_client.tools.execute.return_value = {
            "data": {
                "messageText": "Full email body",
                "subject": "PO-001",
                "sender": "user@example.com",
            }
        }

        mgr = ComposioToolManager(api_key="test-key")
        result = mgr.get_email_message(message_id="msg-123")

        mock_client.tools.execute.assert_called_once_with(
            "GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID",
            user_id="default",
            arguments={
                "message_id": "msg-123",
                "user_id": "me",
            },
        )
        assert result["messageText"] == "Full email body"
        assert result["subject"] == "PO-001"

    @patch("src.services.tools.composio.Composio")
    def test_returns_empty_dict_when_no_data_key(self, mock_composio_cls):
        mock_client = MagicMock()
        mock_composio_cls.return_value = mock_client
        mock_client.tools.execute.return_value = {}

        mgr = ComposioToolManager(api_key="test-key")
        result = mgr.get_email_message(message_id="msg-123")

        assert result == {}


class TestErrorHandling:
    @patch("src.services.tools.composio.Composio")
    def test_composio_error_propagates(self, mock_composio_cls):
        mock_client = MagicMock()
        mock_composio_cls.return_value = mock_client
        mock_client.tools.execute.side_effect = RuntimeError("Composio API error")

        mgr = ComposioToolManager(api_key="test-key")

        with pytest.raises(RuntimeError, match="Composio API error"):
            mgr.send_email(to="user@example.com", subject="Test", body="Hello")
