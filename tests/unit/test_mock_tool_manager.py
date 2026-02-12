"""Unit tests for MockToolManager."""
from src.services.tools.mock import MockToolManager


class TestMockToolManager:
    def test_send_email_captures_call_with_all_args(self):
        mock = MockToolManager()
        result = mock.send_email(
            to="test@example.com",
            subject="Test Subject",
            body="Test body",
            thread_id="thread_123",
        )
        assert result == {"status": "ok", "mock": True}
        assert len(mock.all_calls) == 1
        call = mock.all_calls[0]
        assert call["action"] == "send_email"
        assert call["to"] == "test@example.com"
        assert call["subject"] == "Test Subject"
        assert call["body"] == "Test body"
        assert call["thread_id"] == "thread_123"

    def test_send_email_thread_id_defaults_to_none(self):
        mock = MockToolManager()
        mock.send_email(to="a@b.com", subject="S", body="B")
        assert mock.all_calls[0]["thread_id"] is None

    def test_append_sheet_row_captures_call(self):
        mock = MockToolManager()
        result = mock.append_sheet_row(
            spreadsheet_id="sheet_abc",
            values=["PO-001", "Acme", "Madrid"],
        )
        assert result == {"status": "ok", "mock": True}
        assert len(mock.all_calls) == 1
        call = mock.all_calls[0]
        assert call["action"] == "append_sheet_row"
        assert call["spreadsheet_id"] == "sheet_abc"
        assert call["values"] == ["PO-001", "Acme", "Madrid"]

    def test_get_email_attachment_captures_call_returns_bytes(self):
        mock = MockToolManager()
        result = mock.get_email_attachment(message_id="msg_001", attachment_id="att_001")
        assert isinstance(result, bytes)
        assert result == b""
        assert len(mock.all_calls) == 1
        call = mock.all_calls[0]
        assert call["action"] == "get_email_attachment"
        assert call["message_id"] == "msg_001"
        assert call["attachment_id"] == "att_001"

    def test_emails_sent_filters_only_email_calls(self):
        mock = MockToolManager()
        mock.send_email(to="a@b.com", subject="S1", body="B1")
        mock.append_sheet_row(spreadsheet_id="sheet", values=["v"])
        mock.send_email(to="c@d.com", subject="S2", body="B2")
        assert len(mock.emails_sent) == 2
        assert all(c["action"] == "send_email" for c in mock.emails_sent)

    def test_sheet_rows_added_filters_only_sheet_calls(self):
        mock = MockToolManager()
        mock.send_email(to="a@b.com", subject="S", body="B")
        mock.append_sheet_row(spreadsheet_id="s1", values=["a"])
        mock.append_sheet_row(spreadsheet_id="s2", values=["b"])
        assert len(mock.sheet_rows_added) == 2
        assert all(c["action"] == "append_sheet_row" for c in mock.sheet_rows_added)

    def test_all_calls_returns_everything(self):
        mock = MockToolManager()
        mock.send_email(to="a@b.com", subject="S", body="B")
        mock.append_sheet_row(spreadsheet_id="s", values=["v"])
        mock.get_email_attachment(message_id="m", attachment_id="a")
        assert len(mock.all_calls) == 3

    def test_reset_clears_all_calls(self):
        mock = MockToolManager()
        mock.send_email(to="a@b.com", subject="S", body="B")
        mock.append_sheet_row(spreadsheet_id="s", values=["v"])
        assert len(mock.all_calls) == 2
        mock.reset()
        assert len(mock.all_calls) == 0
        assert len(mock.emails_sent) == 0
        assert len(mock.sheet_rows_added) == 0

    def test_multiple_calls_accumulate_correctly(self):
        mock = MockToolManager()
        for i in range(5):
            mock.send_email(to=f"user{i}@test.com", subject=f"S{i}", body=f"B{i}")
        assert len(mock.emails_sent) == 5
        assert mock.emails_sent[3]["to"] == "user3@test.com"
