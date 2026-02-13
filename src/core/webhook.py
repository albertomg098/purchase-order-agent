from pydantic import BaseModel


class WebhookPayload(BaseModel):
    """Inbound email webhook payload from Composio trigger."""
    message_id: str
    subject: str
    body: str
    sender: str
    has_attachment: bool
    attachment_ids: list[str] = []
    thread_id: str | None = None


# --- Composio TriggerEvent Pydantic models ---


class ComposioGmailAttachment(BaseModel):
    id: str
    name: str | None = None
    mimeType: str | None = None


class ComposioGmailData(BaseModel):
    message_id: str
    thread_id: str | None = None
    subject: str = ""
    sender: str = ""
    message_text: str = ""
    attachment_list: list[ComposioGmailAttachment] = []


class ComposioWebhookPayload(BaseModel):
    """Pydantic model for validating Composio TriggerEvent webhook payload.

    Composio sends a TriggerEvent envelope with trigger metadata and the
    Gmail-specific data nested in the `payload` field.

    If the real payload differs from this model, FastAPI returns 422
    with the exact validation error — making debugging trivial.
    """
    trigger_slug: str | None = None
    payload: ComposioGmailData


def parse_composio_webhook(payload: ComposioWebhookPayload) -> WebhookPayload:
    """Convert a validated Composio webhook payload into our domain model."""
    data = payload.payload
    attachments = data.attachment_list
    return WebhookPayload(
        message_id=data.message_id,
        subject=data.subject,
        body=data.message_text,
        sender=data.sender,
        has_attachment=len(attachments) > 0,
        attachment_ids=[a.id for a in attachments],
        thread_id=data.thread_id,
    )
