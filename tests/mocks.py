from src.services.llm.base import LLMService
from src.services.ocr.base import OCRService


class MockLLM(LLMService):
    """Returns pre-configured responses for testing."""

    def __init__(self, structured_response=None, text_response="", should_raise: Exception | None = None):
        self._structured = structured_response
        self._text = text_response
        self._should_raise = should_raise

    def structured_output(self, messages, response_model):
        if self._should_raise:
            raise self._should_raise
        return self._structured

    def generate_text(self, messages):
        if self._should_raise:
            raise self._should_raise
        return self._text


class MockOCR(OCRService):
    """Returns pre-configured OCR text for testing."""

    def __init__(self, text: str = "", should_raise: Exception | None = None):
        self._text = text
        self._should_raise = should_raise

    def extract_text(self, pdf_bytes: bytes) -> str:
        if self._should_raise:
            raise self._should_raise
        return self._text
