from src.services.tools.base import ToolManager


class MockToolManager(ToolManager):
    """Inspectable mock for evaluation. Captures all calls for assertion."""

    def __init__(
        self,
        mock_attachment_bytes: bytes = b"",
        mock_message: dict | None = None,
    ):
        self._calls: list[dict] = []
        self._mock_attachment_bytes = mock_attachment_bytes
        self._mock_message = mock_message or {}

    def send_email(self, to: str, subject: str, body: str, thread_id: str | None = None) -> dict:
        call = {
            "action": "send_email",
            "to": to,
            "subject": subject,
            "body": body,
            "thread_id": thread_id,
        }
        self._calls.append(call)
        return {"status": "ok", "mock": True}

    def append_sheet_row(self, spreadsheet_id: str, values: list[str]) -> dict:
        call = {
            "action": "append_sheet_row",
            "spreadsheet_id": spreadsheet_id,
            "values": values,
        }
        self._calls.append(call)
        return {"status": "ok", "mock": True}

    def get_email_attachment(self, message_id: str, attachment_id: str, file_name: str = "attachment") -> bytes:
        call = {
            "action": "get_email_attachment",
            "message_id": message_id,
            "attachment_id": attachment_id,
        }
        self._calls.append(call)
        return self._mock_attachment_bytes

    def get_email_message(self, message_id: str) -> dict:
        call = {
            "action": "get_email_message",
            "message_id": message_id,
        }
        self._calls.append(call)
        return dict(self._mock_message)

    # --- Inspection API for graders ---

    @property
    def emails_sent(self) -> list[dict]:
        return [c for c in self._calls if c["action"] == "send_email"]

    @property
    def sheet_rows_added(self) -> list[dict]:
        return [c for c in self._calls if c["action"] == "append_sheet_row"]

    @property
    def all_calls(self) -> list[dict]:
        return list(self._calls)

    def reset(self):
        self._calls.clear()
