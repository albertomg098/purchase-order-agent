from typing import TypedDict


class POWorkflowState(TypedDict, total=False):
    # --- Input (populated from webhook) ---
    email_subject: str
    email_body: str
    email_sender: str
    email_message_id: str
    has_attachment: bool
    pdf_bytes: bytes | None

    # --- Classification ---
    is_valid_po: bool
    po_id: str | None
    classification_reason: str

    # --- Extraction ---
    raw_ocr_text: str
    extracted_data: dict | None          # PurchaseOrder.model_dump()
    field_confidences: dict[str, float]
    extraction_warnings: list[str]

    # --- Validation ---
    validation_errors: list[str]
    missing_fields: list[str]

    # --- Actions & tracking ---
    sheet_row_added: bool
    confirmation_email_sent: bool
    missing_info_email_sent: bool
    actions_log: list[str]
    trajectory: list[str]                # node names visited

    # --- Final ---
    final_status: str                    # "completed" | "missing_info" | "skipped" | "error"
