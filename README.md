# PO Agent

AI agent for automated purchase order intake and fulfillment. An email arrives via webhook, the agent classifies whether it's a valid PO, extracts structured data from the attached PDF using OCR + LLM, validates completeness, logs the order in Google Sheets, and sends a confirmation (or missing-info request) back to the sender.

The project follows an **eval-first** methodology: the evaluation framework (graders, scenarios, PDF fixtures) was designed before the agent itself. This ensures every node is testable against ground-truth expectations from day one, and prevents regressions as the pipeline evolves.

215 unit tests, 15 integration tests, 5 graders, 25 eval scenarios across 5 categories. All eval thresholds met.

## Architecture

```
                                ┌──────────┐
                  Gmail ──────▶ │ Composio │
                                │ Trigger  │
                                └────┬─────┘
                                     │ webhook POST
                                     ▼
                              ┌─────────────┐
                              │   FastAPI    │
                              │  /webhook/   │
                              │   email      │
                              └──────┬───────┘
                                     │ background task
                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LangGraph Workflow                         │
│                                                                 │
│  classify ──┬──▶ extract ──▶ validate ──▶ track ──▶ notify ──┐ │
│             │                                                 │ │
│             └──────────────────────────────────────────────┐  │ │
│                                                            ▼  ▼ │
│                                                          report │
│                                                            │    │
└────────────────────────────────────────────────────────────┼────┘
                                                             ▼
                                                            END
```

The workflow is **deterministic**, not agentic — LangGraph orchestrates a fixed sequence of nodes with one conditional branch after classification. Each node is a class inheriting `BaseNode(ABC)` that receives its dependencies (LLM, OCR, tools, prompts) via constructor injection.

### Nodes

| Node | Responsibility |
|------|---------------|
| **classify** | Analyzes email subject + body + attachment presence. LLM structured output → `is_valid_po`, `po_id`, `reason`. |
| **extract** | PDF → OCR text (Tesseract) → LLM structured output with per-field confidence scores. |
| **validate** | Checks extracted fields for `None`, empty strings, or confidence below threshold. Produces `missing_fields` list. |
| **track** | Appends a row to Google Sheets via Composio with extracted PO data. |
| **notify** | LLM generates a confirmation or missing-info email, sent via Composio Gmail. |
| **report** | Consolidates `final_status`: `completed`, `missing_info`, `skipped`, or `error`. |

### Error handling

Every node wraps its logic in try/except. On failure, it sets `error_message` in the workflow state. Downstream nodes check for this guard and pass through without executing. `ReportNode` consolidates the final status.

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.12 | Type hints, modern syntax |
| Workflow | LangGraph | Conditional routing, state management, tracing integration |
| LLM | OpenAI (`gpt-4o-mini`) | Structured outputs via `client.beta.chat.completions.parse()` — server-side constraint, no extra dependency |
| OCR | Tesseract + pdf2image | Handles scanned PDFs (not just digital), demonstrates real OCR pipeline |
| Tools | Composio | Unified API for Gmail + Google Sheets with managed OAuth |
| API | FastAPI | Async webhook handler, background tasks for long-running processing |
| Observability | Opik | Open-source, provider-agnostic tracing + eval experiment tracking |
| Models | Pydantic v2 | Domain models, config, LLM response schemas, webhook validation |
| Tests | pytest | Unit + integration + eval framework |
| Linting | Ruff | Fast, single-tool Python linting |
| Packaging | uv | Fast dependency resolution and lockfile |
| Deployment | Docker + Railway | Multi-stage build, auto-deploy from GitHub |

## Evaluation Framework

The eval framework was the **first thing built** — before any node implementation. This eval-first approach means:

1. Graders define what "correct" means for each metric
2. Scenarios define input/expected-output pairs with PDF fixtures
3. Nodes are implemented to pass the scenarios
4. Regressions are caught immediately

### Graders

| Grader | Metric | How it works |
|--------|--------|-------------|
| **ClassificationAccuracy** | Binary | `actual.is_valid_po == expected.is_valid_po` |
| **ExtractionAccuracy** | Field-level F1 | Compares 7 fields (order_id, customer, pickup, delivery, datetime, driver name/phone). Normalizes whitespace + case. |
| **TrajectoryCorrectness** | Exact match | `actual.trajectory == expected.trajectory` (ordered node list) |
| **ValidationCorrectness** | Set F1 | Precision/recall on `missing_fields` detection |
| **EmailQuality** | Heuristic | 4 checks: length > 50 chars, mentions PO ID, confirmation language, mentions customer. Each = +0.25 |

### Scenario Categories

| Category | Count | Description |
|----------|-------|-------------|
| `happy_path` | Complete POs with all fields | Full pipeline: classify → extract → validate → track → notify → report |
| `not_a_po` | Non-PO emails | Short pipeline: classify → report (skipped) |
| `missing_fields` | POs with incomplete data | Full pipeline but with validation warnings |
| `malformed_pdf` | Corrupted/noisy PDFs | Tests OCR resilience |
| `ambiguous` | Edge cases | Multiple PO IDs, unclear addresses |

### Eval Scores

| Metric | Score | Target |
|--------|-------|--------|
| ClassificationAccuracy | 1.00 | >= 0.95 |
| ExtractionAccuracy | 0.97 | >= 0.85 |
| TrajectoryCorrectness | 1.00 | >= 0.95 |
| ValidationCorrectness | 1.00 | >= 0.85 |
| EmailQuality | 1.00 | >= 0.70 |

### Running Evals

```bash
# All scenarios
uv run python -m evals.run_eval --experiment-name "my-experiment"

# Single category
uv run python -m evals.run_eval --category happy_path

# Sync scenarios to Opik dashboard
uv run python -m evals.sync_dataset
```

## Key Design Decisions & Tradeoffs

**Eval-first (test-first for AI)** — Graders and scenarios were designed before node implementations. This inverts the usual "build then test" flow and ensures every component has measurable acceptance criteria from the start.

**LangGraph over a simple pipeline** — A plain function chain would work for the current linear flow, but LangGraph provides conditional routing (classify → skip or continue), typed state, built-in tracing, and a clear path to adding cycles (e.g., re-entry for missing fields) without rewriting the orchestration layer.

**Tesseract over pdfplumber** — pdfplumber extracts text from digital PDFs but fails on scanned documents. Tesseract handles both, which is critical for real-world POs that are often scanned or photographed.

**Composio direct execution over LLM tool calling** — Nodes decide *what* to do (send email, append row); Composio executes it. This keeps the workflow deterministic — the LLM generates content, not decisions about which tools to call.

**Structured outputs (native `parse()`) over Instructor** — OpenAI's `beta.chat.completions.parse()` enforces the schema server-side via constrained decoding. No extra dependency, no client-side retry logic.

**Opik over LangSmith** — Open-source, provider-agnostic (works with OpenAI, Anthropic, etc.), and supports experiment comparison with metric tracking. Eval results are versioned and comparable across runs.

**Async webhook with `BackgroundTasks`** — The full pipeline (OCR + LLM) takes 30+ seconds. Returning 202 immediately prevents Composio webhook timeouts, while `BackgroundTasks` processes the email asynchronously.

**In-memory webhook deduplication** — Composio sends the same webhook multiple times. A simple `set()` of seen message IDs prevents duplicate processing. Resets on deploy, which is acceptable since Composio's retry window is shorter than deploy cycles.

## Project Structure

```
src/
├── api.py                    # FastAPI webhook endpoint + signature verification
├── config.py                 # AppConfig (Pydantic BaseSettings, YAML + env)
├── builder.py                # WorkflowBuilder (config-driven DI)
├── workflow.py               # LangGraph graph definition
├── core/                     # Domain models, state, LLM response schemas
│   ├── workflow_state.py     # POWorkflowState (TypedDict)
│   ├── purchase_order.py     # PurchaseOrder, ExtractionResult
│   ├── llm_responses.py      # ClassificationResult, LLMExtractionResponse
│   └── webhook.py            # ComposioWebhookPayload, parse_composio_webhook
├── nodes/                    # LangGraph nodes (BaseNode subclasses)
│   ├── base.py, classify.py, extract.py, validate.py
│   ├── track.py, notify.py, report.py
└── services/                 # ABC interfaces + implementations
    ├── llm/      base.py → openai.py
    ├── ocr/      base.py → tesseract.py
    ├── tools/    base.py → composio.py, mock.py
    └── prompt_store/  base.py → local.py

evals/
├── run_eval.py               # Evaluation runner (Opik integration)
├── sync_dataset.py           # Sync scenarios to Opik dashboard
├── graders/                  # 5 metric graders
├── scenarios/                # JSON scenario files (5 categories)
└── fixtures/                 # PDF test fixtures per category

prompts/en/                   # YAML prompt templates
├── classify.yaml             # Classification system + user prompts
├── extract.yaml              # Extraction system + user prompts
└── notify.yaml               # Notification system + confirmation + missing_info

tests/
├── unit/                     # 215 tests, mocked, no API keys
└── integration/              # 15 tests, real LLM/OCR/API calls
```

## Setup & Running

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Tesseract OCR (`apt install tesseract-ocr tesseract-ocr-eng poppler-utils`)
- API keys: OpenAI, Composio, Opik (optional)

### Local Setup

```bash
# Install dependencies
uv sync

# Copy and fill environment variables
cp .env.example .env
# Edit .env with your API keys

# Run tests
uv run pytest tests/unit/              # Fast, no API keys
uv run pytest tests/integration/ -m integration  # Needs OPENAI_API_KEY
uv run ruff check src/ tests/ evals/   # Linting

# Run evals
uv run python -m evals.run_eval --experiment-name "baseline"

# Start locally
uv run uvicorn src.api:app --reload
```

### Docker

```bash
# Build
docker build -t po-agent .

# Run (pass env vars)
docker run -p 8000:8000 --env-file .env po-agent
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `COMPOSIO_API_KEY` | Yes (prod) | Composio API key for Gmail/Sheets |
| `COMPOSIO_USER_ID` | No | Composio entity ID (default: `default`) |
| `COMPOSIO_WEBHOOK_SECRET` | No | Webhook signature verification secret |
| `SPREADSHEET_ID` | Yes (prod) | Google Sheets spreadsheet ID |
| `SHEET_NAME` | No | Sheet tab name (default: `Sheet1`) |
| `OPIK_API_KEY` | No | Opik cloud tracking |
| `OPIK_WORKSPACE` | No | Opik workspace name |
| `OPIK_PROJECT_NAME` | No | Opik project name |

## Improvements

### Scalability

**Webhook processing** — The current architecture processes emails synchronously in a FastAPI `BackgroundTasks` coroutine. This is bound to a single process and a single server. For higher throughput:

- **Task queue**: Replace `BackgroundTasks` with Celery or a Redis-backed queue (e.g., arq, dramatiq). This decouples webhook ingestion from processing, allows horizontal scaling of workers, and provides retry/dead-letter semantics out of the box.
- **Stateful deduplication**: The in-memory `set()` for message deduplication resets on every deploy. A Redis or database-backed dedup store would survive restarts and work across multiple instances.
- **Multi-tenant routing**: The current system processes all emails through a single Composio entity. Supporting multiple tenants would require routing webhooks by sender domain or Composio user ID, with per-tenant config (spreadsheet IDs, reply templates).
- **Concurrent attachment processing**: Currently only the first attachment is processed. Supporting multiple attachments per email would require parallel OCR + extraction, with result merging in the validate node.

### LLM-as-a-Judge

The current `EmailQuality` grader uses heuristic checks (length, keyword presence) which are brittle and don't capture semantic quality. Replacing it with an **LLM-as-a-Judge** approach would provide more nuanced evaluation:

- **Opik GEval integration**: Opik supports `G-Eval` style graders where an LLM scores outputs on criteria like tone, completeness, and accuracy. This would replace the 4-check heuristic with a single LLM call that evaluates email quality on a continuous scale.
- **Multi-dimensional scoring**: An LLM judge could score separately on *professionalism*, *completeness* (does it mention all relevant PO details?), *actionability* (does the recipient know what to do next?), and *accuracy* (does it correctly reflect the extracted data?). This gives richer signal than a single 0-1 score.
- **Calibration challenges**: LLM judges need calibration — they tend to score generously and are sensitive to prompt phrasing. Mitigations include few-shot examples of good/bad emails with target scores, and running the judge on a held-out set with human-annotated quality labels to measure judge-human agreement.
- **Cost/latency tradeoff**: Each eval scenario would require an additional LLM call for the judge, roughly doubling eval cost. This is acceptable for nightly eval runs but too expensive for CI on every commit. A hybrid approach — heuristic grader in CI, LLM judge in scheduled evals — balances cost and quality.
- **Beyond email**: The same LLM-as-a-Judge pattern could evaluate `classification_reason` quality (is the reasoning sound?) and `extraction_warnings` (are warnings helpful and accurate?), areas where heuristic graders are insufficient.
