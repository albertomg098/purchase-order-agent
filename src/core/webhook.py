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
