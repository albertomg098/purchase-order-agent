"""Integration tests with real Composio API calls.

Run with: uv run pytest tests/integration/test_composio_real.py -m composio
Requires: COMPOSIO_API_KEY, COMPOSIO_USER_ID, SPREADSHEET_ID, SHEET_NAME in .env
"""
import pytest

from src.config import AppConfig
from src.services.tools.composio import ComposioToolManager

TOOLKIT_VERSIONS = {
    "gmail": "20251027_00",
    "googlesheets": "20251027_00",
}

# Read config from .env via AppConfig (pydantic-settings)
_config = AppConfig()
API_KEY = _config.composio_api_key
USER_ID = _config.composio_user_id
SPREADSHEET_ID = _config.spreadsheet_id
SHEET_NAME = _config.sheet_name

pytestmark = pytest.mark.composio

skip_reason = "Composio env vars not configured (COMPOSIO_API_KEY, COMPOSIO_USER_ID)"
skip_if_no_key = pytest.mark.skipif(not API_KEY or USER_ID == "default", reason=skip_reason)


@pytest.fixture(scope="module")
def composio_mgr():
    return ComposioToolManager(
        api_key=API_KEY,
        user_id=USER_ID,
        toolkit_versions=TOOLKIT_VERSIONS,
        sheet_name=SHEET_NAME,
    )


@skip_if_no_key
class TestRealSendEmail:
    def test_sends_email_and_returns_ok(self, composio_mgr):
        result = composio_mgr.send_email(
            to="alberto.martin.martinmoreno@gmail.com",
            subject="[PO Agent] Integration test email",
            body="Automated integration test — please ignore.",
        )
        assert result["status"] == "ok"
        assert result["result"]["successful"] is True
        assert "id" in result["result"]["data"]

    def test_send_email_returns_message_id(self, composio_mgr):
        result = composio_mgr.send_email(
            to="alberto.martin.martinmoreno@gmail.com",
            subject="[PO Agent] Integration test — message ID check",
            body="Checking that send_email returns a message ID.",
        )
        message_id = result["result"]["data"]["id"]
        assert isinstance(message_id, str)
        assert len(message_id) > 0


@skip_if_no_key
class TestRealAppendSheetRow:
    def test_appends_row_and_returns_ok(self, composio_mgr):
        if not SPREADSHEET_ID:
            pytest.skip("SPREADSHEET_ID not set")

        result = composio_mgr.append_sheet_row(
            spreadsheet_id=SPREADSHEET_ID,
            values=["INT-TEST-001", "Integration Test", "Origin", "Destination", "2026-02-13", "Driver", "+000", "test"],
        )
        assert result["status"] == "ok"
        assert result["result"]["successful"] is True


@skip_if_no_key
class TestRealGetEmailMessage:
    def test_fetches_sent_message(self, composio_mgr):
        # Send an email first, then fetch it
        send_result = composio_mgr.send_email(
            to="alberto.martin.martinmoreno@gmail.com",
            subject="[PO Agent] Fetch test",
            body="This message will be fetched by get_email_message.",
        )
        message_id = send_result["result"]["data"]["id"]

        fetched = composio_mgr.get_email_message(message_id=message_id)
        assert "messageText" in fetched
        assert "Fetch test" in fetched.get("messageText", "") or "Fetch test" in str(fetched)
