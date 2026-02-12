from abc import ABC, abstractmethod


class OCRService(ABC):
    @abstractmethod
    def extract_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes. Returns raw text string."""
        ...
