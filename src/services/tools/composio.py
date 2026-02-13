import base64

import opik
from composio import Composio

from src.services.tools.base import ToolManager


class ComposioToolManager(ToolManager):
    """ToolManager implementation using Composio for real Gmail/Sheets operations."""

    def __init__(
        self,
        api_key: str,
        user_id: str = "default",
        toolkit_versions: dict[str, str] | None = None,
    ):
        self._client = Composio(
            api_key=api_key,
            toolkit_versions=toolkit_versions or {},
        )
        self._user_id = user_id

    @opik.track(name="tool_send_email")
    def send_email(self, to: str, subject: str, body: str, thread_id: str | None = None) -> dict:
        arguments = {
            "recipient_email": to,
            "subject": subject,
            "body": body,
            "is_html": False,
        }
        if thread_id:
            arguments["thread_id"] = thread_id

        result = self._client.tools.execute(
            "GMAIL_SEND_EMAIL",
            user_id=self._user_id,
            arguments=arguments,
        )
        return {"status": "ok", "result": result}

    @opik.track(name="tool_append_sheet_row")
    def append_sheet_row(self, spreadsheet_id: str, values: list[str]) -> dict:
        result = self._client.tools.execute(
            "GOOGLESHEETS_CREATE_SPREADSHEET_ROW",
            user_id=self._user_id,
            arguments={
                "spreadsheet_id": spreadsheet_id,
                "values": values,
            },
        )
        return {"status": "ok", "result": result}

    @opik.track(name="tool_get_attachment")
    def get_email_attachment(self, message_id: str, attachment_id: str) -> bytes:
        result = self._client.tools.execute(
            "GMAIL_GET_ATTACHMENT",
            user_id=self._user_id,
            arguments={
                "message_id": message_id,
                "attachment_id": attachment_id,
                "user_id": "me",
            },
        )
        return base64.b64decode(result["data"])

    @opik.track(name="tool_get_email_message")
    def get_email_message(self, message_id: str) -> dict:
        result = self._client.tools.execute(
            "GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID",
            user_id=self._user_id,
            arguments={
                "message_id": message_id,
                "user_id": "me",
            },
        )
        return result.get("data", {})
