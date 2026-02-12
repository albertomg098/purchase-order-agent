from pydantic import BaseModel


class ClassificationResult(BaseModel):
    """LLM response for email classification."""

    is_valid_po: bool
    po_id: str | None = None
    reason: str


class LLMExtractionResponse(BaseModel):
    """LLM response for PO data extraction."""

    data: dict[str, str | None]
    field_confidences: dict[str, float]
    warnings: list[str] = []
