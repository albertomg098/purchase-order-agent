import hashlib
import hmac
import json
import logging

from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
import opik

from src.config import AppConfig
from src.builder import WorkflowBuilder
from src.core.webhook import ComposioWebhookPayload, parse_composio_webhook

logger = logging.getLogger("po_agent.webhook")


def _verify_signature(body: bytes, secret: str, headers: dict[str, str]) -> None:
    """Verify Composio webhook signature. Raises HTTPException(401) on failure."""
    webhook_id = headers.get("webhook-id", "")
    timestamp = headers.get("webhook-timestamp", "")
    signature_header = headers.get("webhook-signature", "")

    if not webhook_id or not timestamp or not signature_header:
        raise HTTPException(status_code=401, detail="Missing webhook signature headers")

    to_sign = f"{webhook_id}.{timestamp}.{body.decode()}"
    expected = hmac.new(secret.encode(), to_sign.encode(), hashlib.sha256).hexdigest()

    # signature_header format: "v1,<hex_signature>"
    parts = signature_header.split(",", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Invalid signature format")

    received = parts[1]
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


def create_app(config: AppConfig | None = None) -> FastAPI:
    """Factory function for creating the FastAPI app with config."""
    if config is None:
        config = AppConfig.from_yaml("config.yaml")

    builder = WorkflowBuilder(config)
    workflow = builder.build()
    tool_manager = builder.tool_manager
    webhook_secret = config.composio_webhook_secret

    app = FastAPI(title="PO Agent")

    @opik.track(name="po_workflow")
    def process_email(payload: ComposioWebhookPayload):
        """Background task: runs the full workflow (OCR + LLM can take 30s+)."""
        webhook_data = parse_composio_webhook(payload)

        # Fetch full message (webhook snippet may be truncated)
        try:
            full_message = tool_manager.get_email_message(
                message_id=webhook_data.message_id,
            )
        except Exception:
            logger.warning(f"Failed to fetch full message {webhook_data.message_id}, using webhook data")
            full_message = {}
        email_body = full_message.get("messageText", webhook_data.body)
        email_subject = full_message.get("subject", webhook_data.subject)
        email_sender = full_message.get("sender", webhook_data.sender)

        # Fetch PDF attachment if present
        pdf_bytes = None
        if webhook_data.has_attachment:
            try:
                pdf_bytes = tool_manager.get_email_attachment(
                    message_id=webhook_data.message_id,
                    attachment_id=webhook_data.attachment_ids[0],
                )
            except Exception:
                logger.warning(f"Failed to fetch attachment from {webhook_data.message_id}")

        # Build workflow input state
        input_state = {
            "email_subject": email_subject,
            "email_body": email_body,
            "email_sender": email_sender,
            "email_message_id": webhook_data.message_id,
            "has_attachment": webhook_data.has_attachment,
            "pdf_bytes": pdf_bytes,
            "thread_id": webhook_data.thread_id,
            "actions_log": [],
            "trajectory": [],
        }

        result = workflow.invoke(input_state)
        logger.info(f"Workflow completed: status={result.get('final_status')}, po_id={result.get('po_id')}")
        return result

    @app.post("/webhook/email", status_code=202)
    async def handle_email_webhook(request: Request, background_tasks: BackgroundTasks):
        """Receive Composio Gmail trigger webhook. Returns immediately, processes in background."""
        body = await request.body()

        # Verify signature if secret is configured
        if webhook_secret:
            _verify_signature(body, webhook_secret, dict(request.headers))

        # Parse and validate payload
        try:
            payload = ComposioWebhookPayload(**json.loads(body))
        except (json.JSONDecodeError, Exception) as e:
            raise HTTPException(status_code=422, detail=str(e))

        logger.info(f"Webhook received: message_id={payload.payload.message_id}")
        background_tasks.add_task(process_email, payload)
        return {"status": "accepted", "message_id": payload.payload.message_id}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


# Module-level app instance for uvicorn (CMD: uvicorn src.api:app)
app = create_app()
