"""Unit tests for TesseractOCR service (mocked pdf2image and pytesseract)."""
from unittest.mock import MagicMock, patch

from src.services.ocr.tesseract import TesseractOCR


class TestTesseractOCRConstructor:
    def test_defaults_lang_eng_dpi_300(self):
        ocr = TesseractOCR()
        assert ocr._lang == "eng"
        assert ocr._dpi == 300

    def test_accepts_custom_lang_and_dpi(self):
        ocr = TesseractOCR(lang="spa", dpi=150)
        assert ocr._lang == "spa"
        assert ocr._dpi == 150


class TestExtractText:
    @patch("src.services.ocr.tesseract.pytesseract")
    @patch("src.services.ocr.tesseract.convert_from_bytes")
    def test_calls_convert_and_tesseract(self, mock_convert, mock_tess):
        img1 = MagicMock()
        img2 = MagicMock()
        mock_convert.return_value = [img1, img2]
        mock_tess.image_to_string.side_effect = ["Page one text", "Page two text"]

        ocr = TesseractOCR(lang="eng", dpi=300)
        result = ocr.extract_text(b"fake-pdf-bytes")

        mock_convert.assert_called_once_with(b"fake-pdf-bytes", dpi=300)
        assert mock_tess.image_to_string.call_count == 2
        mock_tess.image_to_string.assert_any_call(img1, lang="eng")
        mock_tess.image_to_string.assert_any_call(img2, lang="eng")

    @patch("src.services.ocr.tesseract.pytesseract")
    @patch("src.services.ocr.tesseract.convert_from_bytes")
    def test_concatenates_multiple_pages(self, mock_convert, mock_tess):
        mock_convert.return_value = [MagicMock(), MagicMock()]
        mock_tess.image_to_string.side_effect = ["First page", "Second page"]

        ocr = TesseractOCR()
        result = ocr.extract_text(b"fake-pdf")

        assert "First page" in result
        assert "Second page" in result
        assert result == "First page\nSecond page"

    @patch("src.services.ocr.tesseract.pytesseract")
    @patch("src.services.ocr.tesseract.convert_from_bytes")
    def test_strips_whitespace(self, mock_convert, mock_tess):
        mock_convert.return_value = [MagicMock()]
        mock_tess.image_to_string.return_value = "  some text with spaces  \n\n"

        ocr = TesseractOCR()
        result = ocr.extract_text(b"fake-pdf")

        assert result == "some text with spaces"

    @patch("src.services.ocr.tesseract.pytesseract")
    @patch("src.services.ocr.tesseract.convert_from_bytes")
    def test_empty_pdf_returns_empty_string(self, mock_convert, mock_tess):
        mock_convert.return_value = []

        ocr = TesseractOCR()
        result = ocr.extract_text(b"empty-pdf")

        assert result == ""
        mock_tess.image_to_string.assert_not_called()

    @patch("src.services.ocr.tesseract.pytesseract")
    @patch("src.services.ocr.tesseract.convert_from_bytes")
    def test_single_page(self, mock_convert, mock_tess):
        mock_convert.return_value = [MagicMock()]
        mock_tess.image_to_string.return_value = "Only page"

        ocr = TesseractOCR()
        result = ocr.extract_text(b"one-page-pdf")

        assert result == "Only page"
