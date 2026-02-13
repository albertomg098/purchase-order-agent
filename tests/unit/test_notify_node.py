"""Unit tests for NotifyNode."""
from src.nodes.notify import NotifyNode
from src.services.tools.mock import MockToolManager
from src.services.prompt_store.local import LocalPromptStore
from tests.mocks import MockLLM


FULL_DATA = {
    "order_id": "PO-2025-001",
    "customer": "Acme Corp",
    "pickup_location": "Warehouse A",
    "delivery_location": "Retail Hub B",
    "delivery_datetime": "2025-01-18T08:00:00",
    "driver_name": "Juan Pérez",
    "driver_phone": "+34 600 123 456",
}


def _make_node(text_response="Dear customer, your order is confirmed.", should_raise=None):
    llm = MockLLM(text_response=text_response, should_raise=should_raise)
    tools = MockToolManager()
    prompt_store = LocalPromptStore("prompts", language="en")
    return NotifyNode(llm=llm, tools=tools, prompt_store=prompt_store), tools


class TestNotifyNodeConfirmation:
    def test_sends_confirmation_email(self):
        node, tools = _make_node(text_response="Your order PO-2025-001 is confirmed.")
        state = {
            "is_valid_po": True,
            "po_id": "PO-2025-001",
            "extracted_data": FULL_DATA,
            "missing_fields": [],
            "email_sender": "orders@acme.com",
        }

        result = node(state)

        emails = tools.emails_sent
        assert len(emails) == 1
        assert emails[0]["to"] == "orders@acme.com"
        assert "PO-2025-001" in emails[0]["subject"]
        assert result["confirmation_email_sent"] is True

    def test_email_body_from_llm(self):
        node, tools = _make_node(text_response="Generated email body")
        state = {
            "is_valid_po": True,
            "po_id": "PO-2025-001",
            "extracted_data": FULL_DATA,
            "missing_fields": [],
            "email_sender": "orders@acme.com",
        }

        node(state)

        assert tools.emails_sent[0]["body"] == "Generated email body"


class TestNotifyNodeMissingInfo:
    def test_sends_missing_info_email(self):
        node, tools = _make_node(text_response="Please provide the missing fields.")
        state = {
            "is_valid_po": True,
            "po_id": "PO-2025-001",
            "extracted_data": FULL_DATA,
            "missing_fields": ["driver_phone", "delivery_datetime"],
            "email_sender": "orders@acme.com",
        }

        result = node(state)

        emails = tools.emails_sent
        assert len(emails) == 1
        assert emails[0]["to"] == "orders@acme.com"
        assert result["missing_info_email_sent"] is True


class TestNotifyNodeSkip:
    def test_skips_when_not_valid_po(self):
        node, tools = _make_node()
        state = {"is_valid_po": False, "trajectory": ["classify"]}

        result = node(state)

        assert tools.emails_sent == []
        assert "confirmation_email_sent" not in result
        assert result["trajectory"] == ["classify", "notify"]


class TestNotifyNodeTrajectory:
    def test_trajectory_updated(self):
        node, _ = _make_node()
        state = {
            "is_valid_po": True,
            "po_id": "PO-2025-001",
            "extracted_data": FULL_DATA,
            "missing_fields": [],
            "email_sender": "orders@acme.com",
            "trajectory": ["classify", "extract", "validate", "track"],
        }

        result = node(state)

        assert result["trajectory"] == ["classify", "extract", "validate", "track", "notify"]


class TestNotifyNodeErrorHandling:
    def test_llm_error_sets_error_status(self):
        node, _ = _make_node(should_raise=RuntimeError("LLM down"))
        state = {
            "is_valid_po": True,
            "po_id": "PO-2025-001",
            "extracted_data": FULL_DATA,
            "missing_fields": [],
            "email_sender": "orders@acme.com",
        }

        result = node(state)

        assert result["final_status"] == "error"
        assert "NotifyNode failed" in result["error_message"]

    def test_error_guard_passes_through(self):
        node, tools = _make_node()
        state = {
            "final_status": "error",
            "error_message": "Previous failure",
            "trajectory": ["classify", "extract"],
        }

        result = node(state)

        assert result["trajectory"] == ["classify", "extract", "notify"]
        assert tools.emails_sent == []
