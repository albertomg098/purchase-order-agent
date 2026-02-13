"""Integration tests for ExtractNode with real LLM + real OCR.

Requires system dependencies: tesseract-ocr, poppler-utils
"""
from pathlib import Path

import pytest

from src.services.llm.openai import OpenAILLM
from src.services.ocr.tesseract import TesseractOCR
from src.services.prompt_store.local import LocalPromptStore
from src.nodes.extract import ExtractNode


FIXTURES_DIR = Path("evals/fixtures")

EXPECTED_FIELDS = [
    "order_id", "customer", "pickup_location", "delivery_location",
    "delivery_datetime", "driver_name", "driver_phone",
]


@pytest.fixture
def extract_node():
    ocr = TesseractOCR()
    llm = OpenAILLM(model="gpt-4o-mini")
    prompt_store = LocalPromptStore("prompts", language="en")
    return ExtractNode(ocr=ocr, llm=llm, prompt_store=prompt_store)


@pytest.mark.integration
class TestExtractLLMHappyPath:
    def test_extracts_fields_from_happy_path_pdf(self, extract_node):
        pdf_path = FIXTURES_DIR / "happy_path" / "complete_01.pdf"
        assert pdf_path.exists(), f"PDF fixture not found: {pdf_path}"
        pdf_bytes = pdf_path.read_bytes()

        state = {
            "is_valid_po": True,
            "pdf_bytes": pdf_bytes,
        }

        result = extract_node(state)

        assert result.get("raw_ocr_text"), "OCR should produce text"
        assert result.get("extracted_data") is not None, "LLM should extract data"

        extracted = result["extracted_data"]
        for field in EXPECTED_FIELDS:
            assert field in extracted, f"Field '{field}' missing from extraction"

        assert result["extracted_data"]["order_id"] is not None
        assert result["extracted_data"]["customer"] is not None
        assert "extract" in result["trajectory"]

    def test_field_confidences_present(self, extract_node):
        pdf_path = FIXTURES_DIR / "happy_path" / "complete_01.pdf"
        pdf_bytes = pdf_path.read_bytes()

        state = {
            "is_valid_po": True,
            "pdf_bytes": pdf_bytes,
        }

        result = extract_node(state)

        confidences = result.get("field_confidences", {})
        assert len(confidences) > 0, "Should have confidence scores"
        for field, score in confidences.items():
            assert 0.0 <= score <= 1.0, f"Confidence for {field} out of range: {score}"
