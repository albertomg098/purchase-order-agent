from src.services.tools.base import ToolManager


class ComposioToolManager(ToolManager):
    """Composio-based tool manager for email and Google Sheets integration."""

    def send_email(self, to: str, subject: str, body: str, thread_id: str | None = None) -> dict:
        raise NotImplementedError("ComposioToolManager will be implemented in Phase 3")

    def append_sheet_row(self, spreadsheet_id: str, values: list[str]) -> dict:
        raise NotImplementedError("ComposioToolManager will be implemented in Phase 3")

    def get_email_attachment(self, message_id: str, attachment_id: str) -> bytes:
        raise NotImplementedError("ComposioToolManager will be implemented in Phase 3")

    def get_email_message(self, message_id: str) -> dict:
        raise NotImplementedError("ComposioToolManager will be implemented in Phase 3")
