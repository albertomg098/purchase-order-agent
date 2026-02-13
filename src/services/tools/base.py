from abc import ABC, abstractmethod


class ToolManager(ABC):
    @abstractmethod
    def send_email(self, to: str, subject: str, body: str, thread_id: str | None = None) -> dict:
        """Send an email. Returns result dict with at least {"status": "ok"|"error"}."""
        ...

    @abstractmethod
    def append_sheet_row(self, spreadsheet_id: str, values: list[str]) -> dict:
        """Append a row to a Google Sheet. Returns result dict."""
        ...

    @abstractmethod
    def get_email_attachment(self, message_id: str, attachment_id: str, file_name: str = "attachment") -> bytes:
        """Download an email attachment. Returns raw bytes."""
        ...

    @abstractmethod
    def get_email_message(self, message_id: str) -> dict:
        """Fetch full email message by ID. Returns dict with messageText, subject, sender, etc."""
        ...
