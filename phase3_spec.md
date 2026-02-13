# Phase 3 Implementation Spec: Composio Integration + FastAPI Webhook

## Context

Phase 2 delivered all 6 working nodes, real LLM/OCR services, Opik tracing, and passing evals (203 tests, all thresholds met). Phase 3 connects the agent to the real world: Composio for Gmail/Sheets operations, and a FastAPI endpoint to receive email webhooks.

**Key principles** (carried forward):
- **Test-first (RED → GREEN)**: Non-negotiable.
- **Interface stays the same**: ComposioToolManager implements the existing `ToolManager` ABC. No node changes needed.
- **Evals still pass**: All existing unit tests and eval scores must remain intact.

## What's IN Phase 3

1. ComposioToolManager (implements ToolManager ABC using Composio SDK)
2. FastAPI webhook endpoint (receives Composio Gmail trigger events)
3. Composio authentication setup (Gmail + Google Sheets OAuth)
4. Integration tests with real Composio calls
5. End-to-end manual test (send real email → agent processes → reply + sheet row)

## What's NOT in Phase 3

- Docker → Phase 4
- README / deliverable packaging → Phase 4
- EmailQualityLLM grader (future TODO)
- Re-entry for missing fields

---

## Composio SDK Reference (for Claude Code)

### Toolkit Versions (REQUIRED)

Composio SDK v0.9+ requires explicit toolkit versions. Without them, `tools.execute()` throws `ToolVersionRequiredError`.

```python
composio = Composio(
    api_key=config.composio_api_key,
    toolkit_versions={
        "gmail": "20251027_00",
        "googlesheets": "20251027_00",
    }
)
```

### Direct Tool Execution (our approach)

We use Composio as a **service layer**, NOT as an LLM tool provider. Our LLM doesn't call Composio tools — our nodes call them deterministically via `ComposioToolManager`.

```python
from composio import Composio

composio = Composio(api_key="your_composio_key")

# Direct execution — no LLM involved
result = composio.tools.execute(
    "GMAIL_SEND_EMAIL",
    user_id="default",
    arguments={
        "recipient_email": "customer@example.com",
        "subject": "PO Confirmation",
        "body": "Your order has been received...",
        "is_html": False,
    }
)
```

### Key Composio Concepts

- **user_id**: All tools are scoped to a user. For single-tenant, use `"default"`.
- **Toolkits**: Collections of tools (e.g., `gmail`, `googlesheets`).
- **Authentication**: OAuth2 handled by Composio. User must authenticate via Composio dashboard or CLI before tools work.
- **Tool names**: Uppercase slugs like `GMAIL_SEND_EMAIL`, `GMAIL_GET_ATTACHMENT`, `GOOGLESHEETS_BATCH_UPDATE`.

### Gmail Tools We Need

| Tool | Description | Used By |
|---|---|---|
| `GMAIL_SEND_EMAIL` | Send email with to, subject, body | NotifyNode via ToolManager.send_email() |
| `GMAIL_GET_ATTACHMENT` | Get attachment by message_id + attachment_id | Webhook handler (fetch PDF) |
| `GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID` | Get full message (body, subject, sender) | Webhook handler (snippet may be truncated) |

### Google Sheets Tools We Need

| Tool | Description | Used By |
|---|---|---|
| `GOOGLESHEETS_CREATE_SPREADSHEET_ROW` | Append a row to spreadsheet | TrackNode via ToolManager.append_sheet_row() |

### Triggers (Webhook)

Composio can trigger a webhook when a new Gmail message arrives:

```python
# Setup trigger (done once during configuration, not in code)
# Composio dashboard: Triggers → Gmail → New Email → Configure webhook URL
```

The webhook payload (V3 format) looks like:
```json
{
    "log_id": "log_xxx",
    "timestamp": "2026-02-13T...",
    "type": "gmail_new_gmail_message",
    "data": {
        "connection_id": "...",
        "messageId": "msg-123",
        "threadId": "thread-456",
        "subject": "PO-2024-001 Order",
        "sender": "customer@example.com",
        "snippet": "Please find attached...",
        "attachments": [{"attachmentId": "att-789", "filename": "po.pdf", ...}]
    }
}
```

**Important**: The exact payload shape may vary. At implementation time, configure a real trigger and inspect the actual payload before coding the parser.

---

## ToolManager ABC Changes (Breaking)

Phase 1's `ToolManager` ABC needs two additions. These are breaking changes that require updating MockToolManager and existing tests.

### Changes to `src/services/tools/base.py`:
```python
class ToolManager(ABC):
    @abstractmethod
    def send_email(self, to: str, subject: str, body: str, thread_id: str | None = None) -> dict:
        """Send email. thread_id enables replying in same Gmail thread."""
        ...

    @abstractmethod
    def append_sheet_row(self, spreadsheet_id: str, values: list[str]) -> dict:
        """Append a row to a Google Sheet."""
        ...

    @abstractmethod
    def get_email_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Fetch email attachment as raw bytes."""
        ...

    @abstractmethod
    def get_email_message(self, message_id: str) -> dict:
        """Fetch full email message by ID. Returns dict with messageText, subject, sender, etc."""
        ...
```

### Changes to `MockToolManager`:
```python
def send_email(self, to: str, subject: str, body: str, thread_id: str | None = None) -> dict:
    self.actions_log.append({"action": "send_email", "to": to, "subject": subject, "body": body, "thread_id": thread_id})
    return {"status": "ok", "message_id": "mock-msg-id"}

def get_email_attachment(self, message_id: str, attachment_id: str) -> bytes:
    self.actions_log.append({"action": "get_attachment", "message_id": message_id, "attachment_id": attachment_id})
    return self._mock_attachment_bytes  # Configurable in constructor, default b""

def get_email_message(self, message_id: str) -> dict:
    self.actions_log.append({"action": "get_message", "message_id": message_id})
    return self._mock_message  # Configurable in constructor, default {}
```

### Impact on existing tests:
- Update `MockToolManager.__init__` to accept optional `mock_attachment_bytes: bytes = b""`
- Existing `send_email` calls that don't pass `thread_id` still work (default `None`)
- `get_email_attachment` is new — no existing tests call it, so no breakage there
- Run `uv run pytest tests/unit/` after changes to verify nothing breaks

---

## ComposioToolManager Implementation

```python
import opik
from composio import Composio
from src.services.tools.base import ToolManager


class ComposioToolManager(ToolManager):
    """ToolManager implementation using Composio for real Gmail/Sheets operations."""

    def __init__(self, api_key: str, user_id: str = "default", toolkit_versions: dict[str, str] | None = None):
        self._client = Composio(
            api_key=api_key,
            toolkit_versions=toolkit_versions or {},
        )
        self._user_id = user_id

    @opik.track(name="tool_send_email")
    def send_email(self, to: str, subject: str, body: str, thread_id: str | None = None) -> dict:
        arguments = {
            "recipient_email": to,
            "subject": subject,
            "body": body,
            "is_html": False,
        }
        if thread_id:
            arguments["thread_id"] = thread_id

        result = self._client.tools.execute(
            "GMAIL_SEND_EMAIL",
            user_id=self._user_id,
            arguments=arguments,
        )
        return {"status": "ok", "result": result}

    @opik.track(name="tool_append_sheet_row")
    def append_sheet_row(self, spreadsheet_id: str, values: list[str]) -> dict:
        result = self._client.tools.execute(
            "GOOGLESHEETS_CREATE_SPREADSHEET_ROW",
            user_id=self._user_id,
            arguments={
                "spreadsheet_id": spreadsheet_id,
                "values": values,
            },
        )
        return {"status": "ok", "result": result}

    @opik.track(name="tool_get_attachment")
    def get_email_attachment(self, message_id: str, attachment_id: str) -> bytes:
        result = self._client.tools.execute(
            "GMAIL_GET_ATTACHMENT",
            user_id=self._user_id,
            arguments={
                "message_id": message_id,
                "attachment_id": attachment_id,
                "user_id": "me",
            },
        )
        # Result contains base64-encoded data — decode to bytes
        import base64
        return base64.b64decode(result["data"])

    @opik.track(name="tool_get_email_message")
    def get_email_message(self, message_id: str) -> dict:
        result = self._client.tools.execute(
            "GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID",
            user_id=self._user_id,
            arguments={
                "message_id": message_id,
                "user_id": "me",
            },
        )
        return result.get("data", {})
```

**Note**: The exact argument names and response shapes for Composio tools must be verified at implementation time. Use `composio generate` CLI or the Composio dashboard to inspect tool schemas. The code above is reference — adapt to actual API.

---

## FastAPI Webhook Endpoint

```python
# src/api.py
import logging
from fastapi import FastAPI, BackgroundTasks
import opik

from src.config import AppConfig
from src.builder import WorkflowBuilder
from src.core.webhook import ComposioWebhookPayload, parse_composio_webhook

logger = logging.getLogger("po_agent.webhook")

app = FastAPI(title="PO Agent")


def create_app(config: AppConfig | None = None) -> FastAPI:
    """Factory function for creating the FastAPI app with config."""
    if config is None:
        config = AppConfig.from_yaml("config.yaml")

    builder = WorkflowBuilder(config)
    workflow = builder.build()
    tool_manager = builder.tool_manager

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
```

**Why async via BackgroundTasks**: The workflow involves OCR + multiple LLM calls and can take 30+ seconds. Without background processing, Composio would timeout waiting for the webhook response and potentially retry, causing duplicate processing. With `BackgroundTasks`, the endpoint responds with `202 Accepted` immediately. No extra infrastructure needed (no celery, no redis).

**Tradeoff**: The webhook response no longer contains workflow results. Results are visible via: Opik dashboard (traces), Google Sheet (new row), and server logs.

### Webhook Payload Parsing

**Two-phase approach for payload safety:**

**Phase A (Step 4 — before real testing):** Build parser based on Composio V3 docs. Use a Pydantic model for strict validation:

```python
from pydantic import BaseModel


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
```

Use this model directly in the FastAPI endpoint:
```python
@app.post("/webhook/email")
async def handle_email_webhook(payload: ComposioWebhookPayload):
    # payload is already validated by Pydantic
    webhook_data = parse_composio_webhook(payload)
    ...
```

**Phase B (Step 8a — real testing):** Send a real email, check logs for raw payload, and adapt the Pydantic model to match actual structure. The model ensures any future payload changes break loudly with clear errors.

Create a `src/core/webhook.py` parser that converts raw payload → `WebhookPayload` (already defined in Phase 1):

```python
def parse_composio_webhook(raw: dict) -> WebhookPayload:
    """Parse Composio Gmail trigger webhook into our domain model."""
    data = raw.get("data", {})
    attachments = data.get("attachments", [])
    return WebhookPayload(
        message_id=data.get("messageId", ""),
        subject=data.get("subject", ""),
        body=data.get("snippet", ""),
        sender=data.get("sender", ""),
        has_attachment=len(attachments) > 0,
        attachment_ids=[a["attachmentId"] for a in attachments],
        thread_id=data.get("threadId"),
    )
```

---

## Builder Updates

Update builder to handle `tool_manager: "composio"`:

```python
# In WorkflowBuilder._init_services()
if self.config.tool_manager == "composio":
    from src.services.tools.composio import ComposioToolManager
    self.tool_manager = ComposioToolManager(
        api_key=self.config.composio_api_key,
        user_id=self.config.composio_user_id,
        toolkit_versions=self.config.composio_toolkit_versions,
    )
```

## Config Additions

```python
# New fields in AppConfig
composio_api_key: str | None = None       # from COMPOSIO_API_KEY env
composio_user_id: str = "default"         # from COMPOSIO_USER_ID env (per-user in multi-tenant)
spreadsheet_id: str | None = None         # from SPREADSHEET_ID env (per-user in multi-tenant)
```

```yaml
# config.yaml — static config, not per-user
tool_manager: composio              # Changed from "mock" for production
composio_toolkit_versions:          # Pinned versions, not per-user
  gmail: "20251027_00"
  googlesheets: "20251027_00"
```

Update `.env.example`:
```bash
# Composio
COMPOSIO_API_KEY=your_composio_api_key
COMPOSIO_USER_ID=your_entity_id        # Entity ID from Composio dashboard
SPREADSHEET_ID=1aBcDeFg...             # Google Sheet for PO tracking
```

**Scaling note**: In a multi-tenant setup, `COMPOSIO_USER_ID` and `SPREADSHEET_ID` would be injected per-user (e.g. from a database lookup based on the incoming email domain). Toolkit versions stay in YAML because they're infrastructure config, not user-specific.

---

## Composio Setup (One-Time, Manual)

Before any code runs against real services, these steps must be done manually:

1. **Create Composio account** at composio.dev
2. **Get API key** from dashboard
3. **Connect Gmail**: Dashboard → Connected Accounts → Gmail → OAuth flow
4. **Connect Google Sheets**: Dashboard → Connected Accounts → Google Sheets → OAuth flow
5. **Create Gmail trigger**: Dashboard → Triggers → Gmail → New Email → Set webhook URL to `http://your-server/webhook/email`
6. **Create a Google Sheet** for tracking POs, note the spreadsheet_id
7. **Test connection**: Run `composio.tools.execute("GMAIL_SEND_EMAIL", ...)` manually to verify

---

## Implementation Order

**CRITICAL: Test-first (RED → GREEN) approach is mandatory.**

### Step 1: ToolManager ABC changes + Config updates
- Add `thread_id` param to `send_email` in `ToolManager` ABC (with default `None`)
- Add `get_email_attachment` abstract method to `ToolManager` ABC
- Add `get_email_message` abstract method to `ToolManager` ABC
- Update `MockToolManager` with new methods and constructor params (`mock_attachment_bytes`, `mock_message`)
- Add `composio_api_key`, `composio_user_id`, `composio_toolkit_versions` to AppConfig
- Update `.env.example`
- Update existing tests that instantiate MockToolManager if needed
- Run `uv run pytest tests/unit/` → all 203+ tests STILL PASS (critical check)

### Step 2: ComposioToolManager (TEST FIRST)
- Write `tests/unit/test_composio_tool_manager.py`:
  - Test constructor accepts api_key, user_id, toolkit_versions
  - Test send_email calls composio.tools.execute with `GMAIL_SEND_EMAIL` and correct arguments (mock Composio client)
  - Test send_email passes thread_id when provided
  - Test append_sheet_row calls with `GOOGLESHEETS_CREATE_SPREADSHEET_ROW` (mock Composio client)
  - Test get_email_attachment calls `GMAIL_GET_ATTACHMENT` and decodes base64 (mock Composio client)
  - Test get_email_message calls `GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID` (mock Composio client)
  - Test error handling when Composio call fails
- Run tests → FAIL (RED)
- Implement `src/services/tools/composio.py`
- Run tests → PASS (GREEN)

### Step 3: Builder update
- Update builder to instantiate ComposioToolManager when `tool_manager == "composio"`
- Update `tests/integration/test_builder.py`:
  - Test builder with composio config creates ComposioToolManager
  - Test builder still creates MockToolManager for eval config
- Run tests → PASS

### Step 4: Webhook payload parser + validation model (TEST FIRST)
- Write `tests/unit/test_webhook_parser.py`:
  - Test `ComposioWebhookPayload` Pydantic model validates correct payload
  - Test model rejects payload with missing `data.messageId` (ValidationError)
  - Test `parse_composio_webhook` converts validated payload into `WebhookPayload`
  - Test handles missing optional fields gracefully (no threadId, no attachments)
  - Test extracts attachment IDs correctly
- Run tests → FAIL (RED)
- Implement `src/core/webhook.py` with `ComposioWebhookPayload` model + `parse_composio_webhook` function
- Run tests → PASS (GREEN)

### Step 5: FastAPI endpoint (TEST FIRST)
- Write `tests/integration/test_api.py`:
  - Test health endpoint returns 200
  - Test webhook endpoint returns 202 with `{"status": "accepted", "message_id": ...}`
  - Test webhook validates payload (invalid payload → 422)
  - Test webhook enqueues background task (mock `process_email`, verify it was called)
  - Test `process_email` function directly: parses payload, fetches message, invokes workflow (mock workflow + tool_manager)
- Run tests → FAIL (RED)
- Implement `src/api.py`
- Run tests → PASS (GREEN)

### Step 6: Composio setup + manual verification
- Set up Composio account, connect Gmail + Sheets (manual)
- Set `COMPOSIO_API_KEY` in `.env`
- Write a quick script `scripts/test_composio.py`:
  - Send a test email via Composio
  - Append a test row to a sheet
  - Fetch an attachment from a known email
- Run manually to verify connections work

### Step 7: Integration tests with real Composio
- Write `tests/integration/test_composio_real.py`:
  - Test real send_email via Composio (mark @pytest.mark.composio)
  - Test real append_sheet_row (mark @pytest.mark.composio)
- These require real API keys and authenticated connections
- Add pytest marker: `composio: requires Composio API key and connected accounts`

### Step 8: End-to-end manual test
- Start FastAPI server: `uv run uvicorn src.api:app --reload`
- Expose via ngrok: `ngrok http 8000` → copy the public URL
- Configure Composio trigger webhook URL to `https://your-ngrok-url/webhook/email`
- **Sub-step 8a: Discover real payload format**
  - Send a test email to the connected Gmail account
  - Check server logs for "Raw webhook payload" line
  - Compare with assumed format in `parse_composio_webhook`
  - Adapt parser if needed
- **Sub-step 8b: Full e2e test**
  - Send a real email with PO PDF attachment
  - Verify:
    - Agent classifies correctly
    - Data extracted from PDF
    - Row added to Google Sheet
    - Confirmation email sent back
    - Opik dashboard shows full trace
  - Document the test with screenshots

### Step 9: Verify evals still pass
- Run: `uv run pytest tests/unit/` → all 203+ tests pass
- Run: `uv run python -m evals.run_eval --experiment-name "phase3-verification"` → scores maintained
- Evals continue using MockToolManager (eval config unchanged)

### Final verification
- `uv run pytest tests/unit/` → all pass
- `uv run pytest tests/integration/ -m integration` → all pass
- `uv run ruff check src/ tests/ evals/` → clean
- Manual e2e test documented

---

## Key Constraints

- Use `uv` for ALL package management
- **TEST FIRST**: No implementation without a failing test
- **`__init__.py` files must be empty.** Always use full imports.
- ComposioToolManager implements the same `ToolManager` ABC — no node changes
- Eval runner continues using `MockToolManager` (eval config unchanged)
- Composio integration tests marked with `@pytest.mark.composio` (separate from `@pytest.mark.integration`)
- The exact Composio tool argument names and response shapes MUST be verified at implementation time against actual API
- Webhook payload parser must be adapted to actual Composio trigger payload (log raw payload first)

## Test Summary

| Test file | Tests for | Step |
|---|---|---|
| `tests/unit/test_composio_tool_manager.py` | ComposioToolManager with mocked Composio client | 2 |
| `tests/unit/test_webhook_parser.py` | Webhook payload parsing | 4 |
| `tests/integration/test_api.py` | FastAPI endpoint with TestClient | 5 |
| `tests/integration/test_composio_real.py` | Real Composio calls (requires API key) | 7 |

## Risk Notes

1. **Composio SDK surface area**: The SDK has changed significantly (Tool Router, V3 webhooks). The `composio.tools.execute()` direct execution is the stable path but argument names may differ from docs. Always verify with real calls.
2. **OAuth token expiry**: Composio handles refresh but tokens can expire. The agent should handle `401` errors from Composio gracefully.
3. **Webhook reliability**: Composio webhook delivery is not guaranteed. For production, consider idempotency (check if PO already processed before re-processing).
4. **Rate limits**: Gmail API has rate limits. Composio may throttle. Add retry logic in Phase 4 if needed.
5. **Webhook timeout (mitigated)**: Solved by using `BackgroundTasks` — endpoint returns 202 immediately. However, if the server process crashes mid-workflow, the task is lost (no persistence). For production, consider a proper task queue.
6. **`AppConfig.for_eval()` compatibility**: The eval config factory must continue working after adding Composio fields. Ensure new fields have defaults (`composio_api_key: str | None = None`, `composio_toolkit_versions: dict = {}`). The eval runner never touches Composio — it uses `tool_manager: "mock"`.
7. **Snippet vs full body**: The webhook trigger may only include a `snippet` (truncated preview), not the full email body. The webhook handler addresses this by calling `get_email_message()` to fetch the complete body before invoking the workflow.
8. **Composio tool names**: The tool slugs (`GMAIL_SEND_EMAIL`, `GOOGLESHEETS_CREATE_SPREADSHEET_ROW`, etc.) are based on what was discovered via `composio.tools.get()`. If they don't work at execution time, inspect the actual tool schemas via Composio dashboard or `composio generate` CLI.