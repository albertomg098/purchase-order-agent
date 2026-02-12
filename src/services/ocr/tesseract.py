from src.services.ocr.base import OCRService


class TesseractOCR(OCRService):
    """Tesseract OCR via image-based extraction.

    Internally: PDF bytes → images (via pdf2image) → Tesseract OCR → text.
    This approach handles both native-text PDFs and scanned documents.
    """
    def extract_text(self, pdf_bytes: bytes) -> str:
        raise NotImplementedError("TesseractOCR will be implemented in Phase 2")
