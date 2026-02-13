"""Unit tests for ExtractNode."""
from src.nodes.extract import ExtractNode
from src.core.llm_responses import LLMExtractionResponse
from src.services.prompt_store.local import LocalPromptStore
from tests.mocks import MockLLM, MockOCR


FULL_DATA = {
    "order_id": "PO-2025-001",
    "customer": "Acme Corp",
    "pickup_location": "Warehouse A, Madrid",
    "delivery_location": "Retail Hub B, Barcelona",
    "delivery_datetime": "2025-01-18T08:00:00",
    "driver_name": "Juan Pérez",
    "driver_phone": "+34 600 123 456",
}

FULL_CONFIDENCES = {
    "order_id": 0.95,
    "customer": 0.90,
    "pickup_location": 0.85,
    "delivery_location": 0.80,
    "delivery_datetime": 0.75,
    "driver_name": 0.70,
    "driver_phone": 0.65,
}


def _make_node(ocr_text="OCR output text", llm_response=None, ocr_raise=None, llm_raise=None):
    ocr = MockOCR(text=ocr_text, should_raise=ocr_raise)
    llm = MockLLM(structured_response=llm_response, should_raise=llm_raise)
    prompt_store = LocalPromptStore("prompts", language="en")
    return ExtractNode(ocr=ocr, llm=llm, prompt_store=prompt_store)


def _valid_state(pdf_bytes=b"fake-pdf"):
    return {
        "is_valid_po": True,
        "pdf_bytes": pdf_bytes,
    }


class TestExtractNodeHappyPath:
    def test_full_extraction(self):
        response = LLMExtractionResponse(
            data=FULL_DATA,
            field_confidences=FULL_CONFIDENCES,
            warnings=["Minor OCR artifact"],
        )
        node = _make_node(ocr_text="Purchase Order PO-2025-001...", llm_response=response)

        result = node(_valid_state())

        assert result["extracted_data"] == FULL_DATA
        assert result["field_confidences"] == FULL_CONFIDENCES
        assert result["extraction_warnings"] == ["Minor OCR artifact"]

    def test_partial_extraction(self):
        partial_data = {**FULL_DATA, "driver_phone": None}
        partial_conf = {**FULL_CONFIDENCES, "driver_phone": 0.0}
        response = LLMExtractionResponse(
            data=partial_data,
            field_confidences=partial_conf,
        )
        node = _make_node(llm_response=response)

        result = node(_valid_state())

        assert result["extracted_data"]["driver_phone"] is None
        assert result["field_confidences"]["driver_phone"] == 0.0

    def test_stores_raw_ocr_text(self):
        response = LLMExtractionResponse(data=FULL_DATA, field_confidences=FULL_CONFIDENCES)
        node = _make_node(ocr_text="Raw OCR content here", llm_response=response)

        result = node(_valid_state())

        assert result["raw_ocr_text"] == "Raw OCR content here"

    def test_trajectory_updated(self):
        response = LLMExtractionResponse(data=FULL_DATA, field_confidences=FULL_CONFIDENCES)
        node = _make_node(llm_response=response)

        result = node(_valid_state())

        assert "extract" in result["trajectory"]

    def test_trajectory_appends_to_existing(self):
        response = LLMExtractionResponse(data=FULL_DATA, field_confidences=FULL_CONFIDENCES)
        node = _make_node(llm_response=response)
        state = {**_valid_state(), "trajectory": ["classify"]}

        result = node(state)

        assert result["trajectory"] == ["classify", "extract"]


class TestExtractNodeSkip:
    def test_skips_when_not_valid_po(self):
        response = LLMExtractionResponse(data=FULL_DATA, field_confidences=FULL_CONFIDENCES)
        node = _make_node(llm_response=response)
        state = {"is_valid_po": False, "trajectory": ["classify"]}

        result = node(state)

        assert "extracted_data" not in result
        assert result["trajectory"] == ["classify", "extract"]


class TestExtractNodeErrorHandling:
    def test_ocr_error_sets_error_status(self):
        node = _make_node(ocr_raise=RuntimeError("Poppler not found"))

        result = node(_valid_state())

        assert result["final_status"] == "error"
        assert "ExtractNode failed" in result["error_message"]
        assert "Poppler not found" in result["error_message"]
        assert "extract" in result["trajectory"]

    def test_llm_error_sets_error_status(self):
        node = _make_node(ocr_text="some text", llm_raise=RuntimeError("API timeout"))

        result = node(_valid_state())

        assert result["final_status"] == "error"
        assert "ExtractNode failed" in result["error_message"]
        assert "API timeout" in result["error_message"]

    def test_error_guard_passes_through(self):
        response = LLMExtractionResponse(data=FULL_DATA, field_confidences=FULL_CONFIDENCES)
        node = _make_node(llm_response=response)
        state = {
            **_valid_state(),
            "final_status": "error",
            "error_message": "Previous node failed",
            "trajectory": ["classify"],
        }

        result = node(state)

        assert result["trajectory"] == ["classify", "extract"]
        assert "extracted_data" not in result
