"""Integration tests for ClassifyNode with real LLM calls."""
import pytest

from src.services.llm.openai import OpenAILLM
from src.services.prompt_store.local import LocalPromptStore
from src.nodes.classify import ClassifyNode


@pytest.fixture
def classify_node():
    llm = OpenAILLM(model="gpt-4o-mini")
    prompt_store = LocalPromptStore("prompts", language="en")
    return ClassifyNode(llm=llm, prompt_store=prompt_store)


@pytest.mark.integration
class TestClassifyLLMHappyPath:
    def test_valid_po_email(self, classify_node):
        state = {
            "email_subject": "Purchase Order PO-2025-001",
            "email_body": "Please find attached the purchase order for processing.",
            "email_sender": "orders@acmelogistics.com",
            "has_attachment": True,
        }

        result = classify_node(state)

        assert result["is_valid_po"] is True
        assert result["po_id"] is not None
        assert "classify" in result["trajectory"]

    def test_not_a_po_email(self, classify_node):
        state = {
            "email_subject": "Monthly Logistics Newsletter - March 2025",
            "email_body": "Please find our monthly newsletter attached.",
            "email_sender": "newsletter@logisticsnews.com",
            "has_attachment": True,
        }

        result = classify_node(state)

        assert result["is_valid_po"] is False
        assert "classify" in result["trajectory"]

    def test_no_attachment_email(self, classify_node):
        state = {
            "email_subject": "Purchase Order PO-2025-099",
            "email_body": "Here is the purchase order.",
            "email_sender": "orders@acme.com",
            "has_attachment": False,
        }

        result = classify_node(state)

        assert result["is_valid_po"] is False
        assert "classify" in result["trajectory"]
