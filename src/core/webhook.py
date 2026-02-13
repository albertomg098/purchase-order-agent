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


# --- Composio webhook Pydantic models ---


class ComposioGmailAttachment(BaseModel):
    attachmentId: str
    filename: str | None = None


class ComposioGmailData(BaseModel):
    messageId: str
    threadId: str | None = None
    subject: str = ""
    sender: str = ""
    snippet: str = ""
    attachments: list[ComposioGmailAttachment] = []


class ComposioWebhookPayload(BaseModel):
    """Pydantic model for validating Composio webhook payload.

    If the real payload differs from this model, FastAPI returns 422
    with the exact validation error — making debugging trivial.
    """
    log_id: str | None = None
    timestamp: str | None = None
    type: str | None = None
    data: ComposioGmailData


def parse_composio_webhook(payload: ComposioWebhookPayload) -> WebhookPayload:
    """Convert a validated Composio webhook payload into our domain model."""
    data = payload.data
    attachments = data.attachments
    return WebhookPayload(
        message_id=data.messageId,
        subject=data.subject,
        body=data.snippet,
        sender=data.sender,
        has_attachment=len(attachments) > 0,
        attachment_ids=[a.attachmentId for a in attachments],
        thread_id=data.threadId,
    )
