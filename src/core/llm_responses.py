from pydantic import BaseModel


class ClassificationResult(BaseModel):
    """LLM response for email classification."""

    is_valid_po: bool
    po_id: str | None = None
    reason: str


class ExtractionData(BaseModel):
    """Extracted PO fields from OCR text."""

    order_id: str | None
    customer: str | None
    pickup_location: str | None
    delivery_location: str | None
    delivery_datetime: str | None
    driver_name: str | None
    driver_phone: str | None


class ExtractionConfidences(BaseModel):
    """Confidence scores for each extracted field."""

    order_id: float
    customer: float
    pickup_location: float
    delivery_location: float
    delivery_datetime: float
    driver_name: float
    driver_phone: float


class LLMExtractionResponse(BaseModel):
    """LLM response for PO data extraction."""

    data: ExtractionData
    field_confidences: ExtractionConfidences
    warnings: list[str]
