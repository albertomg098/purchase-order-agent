import opik
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

from src.services.ocr.base import OCRService


class TesseractOCR(OCRService):
    """Tesseract OCR via image-based extraction.

    PDF bytes → images (via pdf2image/poppler) → Tesseract OCR → concatenated text.
    """

    def __init__(self, lang: str = "eng", dpi: int = 300):
        self._lang = lang
        self._dpi = dpi

    @opik.track(name="ocr_extract_text")
    def extract_text(self, pdf_bytes: bytes) -> str:
        images: list[Image.Image] = convert_from_bytes(pdf_bytes, dpi=self._dpi)
        texts = []
        for img in images:
            text = pytesseract.image_to_string(img, lang=self._lang)
            texts.append(text)
        return "\n".join(texts).strip()
