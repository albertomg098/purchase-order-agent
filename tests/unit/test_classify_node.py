"""Unit tests for ClassifyNode."""
from src.nodes.classify import ClassifyNode
from src.core.llm_responses import ClassificationResult
from src.services.prompt_store.local import LocalPromptStore
from tests.mocks import MockLLM


def _make_node(structured_response=None, should_raise=None):
    llm = MockLLM(structured_response=structured_response, should_raise=should_raise)
    prompt_store = LocalPromptStore("prompts", language="en")
    return ClassifyNode(llm=llm, prompt_store=prompt_store)


def _valid_po_state():
    return {
        "email_subject": "Purchase Order PO-2025-001",
        "email_body": "Please find attached the purchase order.",
        "email_sender": "orders@acme.com",
        "has_attachment": True,
    }


class TestClassifyNodeHappyPath:
    def test_valid_po_detected(self):
        response = ClassificationResult(is_valid_po=True, po_id="PO-2025-001", reason="Valid PO with attachment")
        node = _make_node(structured_response=response)

        result = node(_valid_po_state())

        assert result["is_valid_po"] is True
        assert result["po_id"] == "PO-2025-001"
        assert result["classification_reason"] == "Valid PO with attachment"

    def test_non_po_detected(self):
        response = ClassificationResult(is_valid_po=False, reason="Marketing email")
        node = _make_node(structured_response=response)

        result = node(_valid_po_state())

        assert result["is_valid_po"] is False
        assert result["po_id"] is None

    def test_trajectory_updated(self):
        response = ClassificationResult(is_valid_po=True, po_id="PO-001", reason="Valid")
        node = _make_node(structured_response=response)

        result = node(_valid_po_state())

        assert "classify" in result["trajectory"]

    def test_trajectory_appends_to_existing(self):
        response = ClassificationResult(is_valid_po=True, po_id="PO-001", reason="Valid")
        node = _make_node(structured_response=response)
        state = _valid_po_state()
        state["trajectory"] = ["previous"]

        result = node(state)

        assert result["trajectory"] == ["previous", "classify"]


class TestClassifyNodeErrorHandling:
    def test_llm_error_sets_error_status(self):
        node = _make_node(should_raise=RuntimeError("LLM timeout"))

        result = node(_valid_po_state())

        assert result["final_status"] == "error"
        assert "ClassifyNode failed" in result["error_message"]
        assert "LLM timeout" in result["error_message"]
        assert "classify" in result["trajectory"]

    def test_error_guard_passes_through(self):
        response = ClassificationResult(is_valid_po=True, po_id="PO-001", reason="Valid")
        node = _make_node(structured_response=response)
        state = {
            **_valid_po_state(),
            "final_status": "error",
            "error_message": "Previous node failed",
            "trajectory": ["previous"],
        }

        result = node(state)

        assert result["trajectory"] == ["previous", "classify"]
        assert "is_valid_po" not in result
