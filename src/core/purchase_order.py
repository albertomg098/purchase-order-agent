from pydantic import BaseModel, Field
from datetime import datetime


class PurchaseOrder(BaseModel):
    """Canonical purchase order data extracted from a PDF."""
    order_id: str
    customer: str
    pickup_location: str
    delivery_location: str
    delivery_datetime: datetime
    driver_name: str
    driver_phone: str


class ExtractionResult(BaseModel):
    """Result of the PDF extraction process."""
    data: PurchaseOrder | None = None
    field_confidences: dict[str, float] = Field(default_factory=dict)
    raw_ocr_text: str = ""
    warnings: list[str] = Field(default_factory=list)
