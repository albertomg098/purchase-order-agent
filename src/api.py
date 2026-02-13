import logging

from fastapi import FastAPI, BackgroundTasks
import opik

from src.config import AppConfig
from src.builder import WorkflowBuilder
from src.core.webhook import ComposioWebhookPayload, parse_composio_webhook

logger = logging.getLogger("po_agent.webhook")


def create_app(config: AppConfig | None = None) -> FastAPI:
    """Factory function for creating the FastAPI app with config."""
    if config is None:
        config = AppConfig.from_yaml("config.yaml")

    builder = WorkflowBuilder(config)
    workflow = builder.build()
    tool_manager = builder.tool_manager

    app = FastAPI(title="PO Agent")

    @opik.track(name="po_workflow")
    def process_email(payload: ComposioWebhookPayload):
        """Background task: runs the full workflow (OCR + LLM can take 30s+)."""
        webhook_data = parse_composio_webhook(payload)

        # Fetch full message (webhook snippet may be truncated)
        full_message = tool_manager.get_email_message(
            message_id=webhook_data.message_id,
        )
        email_body = full_message.get("messageText", webhook_data.body)
        email_subject = full_message.get("subject", webhook_data.subject)
        email_sender = full_message.get("sender", webhook_data.sender)

        # Fetch PDF attachment if present
        pdf_bytes = None
        if webhook_data.has_attachment:
            pdf_bytes = tool_manager.get_email_attachment(
                message_id=webhook_data.message_id,
                attachment_id=webhook_data.attachment_ids[0],
            )

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
    async def handle_email_webhook(payload: ComposioWebhookPayload, background_tasks: BackgroundTasks):
        """Receive Composio Gmail trigger webhook. Returns immediately, processes in background."""
        logger.info(f"Webhook received: message_id={payload.data.messageId}")
        background_tasks.add_task(process_email, payload)
        return {"status": "accepted", "message_id": payload.data.messageId}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
