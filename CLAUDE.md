# CLAUDE.md

## Project Overview

**po-agent** — AI agent for purchase order intake & fulfillment. Email arrives via Composio Gmail webhook → classify if valid PO → extract PDF data via OCR + LLM → validate → track in Google Sheets → send confirmation email.

**Current state**: Phase 4 complete. 215 unit tests + 15 integration tests passing, all eval thresholds met. Deployed on Railway with Composio webhook connected.

## Tech Stack

- Python 3.12+, `uv` for all package management
- LangGraph (workflow orchestration — deterministic pipeline, not truly agentic)
- OpenAI SDK (`client.beta.chat.completions.parse()` for structured outputs)
- Tesseract + pdf2image (OCR: PDF → images → text)
- Composio (Gmail + Google Sheets via managed OAuth)
- FastAPI (async webhook endpoint with signature verification)
- Opik (tracing + evaluation dashboard)
- Pydantic v2 for all models
- ABC for all service interfaces (not Protocol)
- pytest for tests, ruff for linting
- Docker + Railway for deployment

## Architecture

Service-oriented with dependency injection via builder pattern.

```
src/
├── api.py             # FastAPI webhook endpoint + signature verification
├── config.py          # AppConfig (Pydantic BaseSettings, reads env + YAML)
├── builder.py         # WorkflowBuilder (config-driven service instantiation)
├── workflow.py        # LangGraph graph definition
├── core/              # Domain models, state, LLM response schemas, webhook parsing
├── nodes/             # LangGraph nodes (BaseNode ABC subclasses)
└── services/          # One folder per service (ocr/, llm/, tools/, prompt_store/)

evals/                 # Evaluation framework (scenarios, graders, fixtures)
prompts/en/            # Prompt templates (YAML, organized by language)
tests/
├── unit/              # Isolated tests with mocks (215 tests)
└── integration/       # Real LLM/OCR/API calls (15 tests)
```

### Key patterns

- **Nodes as classes**: Each node inherits `BaseNode(ABC)`, has a `name` class variable and `__call__(state) -> dict`
- **Services injected via constructor**: Nodes receive `LLMService`, `OCRService`, `ToolManager`, `PromptStore` — never instantiate them
- **Config drives everything**: `AppConfig.from_yaml()` or `AppConfig.for_eval()`. Builder reads config to decide which implementations to use
- **PromptStore**: `get_and_render(category, name, params)` returns rendered string. Nodes build the `messages` list themselves
- **MockToolManager**: Captures all calls for grader assertions in evals (not a no-op mock)

### Workflow graph

```
classify → [valid PO]   → extract → validate → track → notify → report → END
classify → [not valid]  → report → END
```

### Error handling

Every node wraps logic in try/except. On error: sets `error_message` in state, downstream nodes check for error guard and pass through. ReportNode consolidates final status.

### Tracing

`@opik.track` on node `__call__` methods and service methods. Root trace created at entrypoint (eval runner or webhook handler). Opik auto-nests spans via Python context variables.

### Webhook

- Composio V3 payload format: `{"metadata": {...}, "data": {gmail_fields}}`
- HMAC-SHA256 signature verification (base64-encoded)
- In-memory deduplication by `message_id` (Composio sends duplicates)
- Sender email extracted from `"Display Name" <email>` format

## Development Conventions

### Non-negotiable rules

1. **`uv` for everything**: `uv run pytest`, `uv add`, `uv run python -m ...`
2. **Test-first (RED → GREEN)**: Write test → confirm FAIL → implement → confirm PASS → commit
3. **`__init__.py` files are always empty**. Use full imports: `from src.core.purchase_order import PurchaseOrder`
4. **After every change**: `uv run pytest tests/unit/` must pass. Never break existing tests.
5. **Show plan → STOP**: Before writing code for any step, show the plan and wait for approval.

### Testing

```bash
uv run pytest tests/unit/           # Fast, no API keys needed
uv run pytest tests/integration/ -m integration  # Needs OPENAI_API_KEY
uv run pytest tests/                # All tests
uv run ruff check src/ tests/ evals/  # Linting
```

- Unit tests use `MockLLM`, `MockOCR` (in `tests/mocks.py`), and `MockToolManager` (in `src/services/tools/mock.py`)
- Integration tests marked with `@pytest.mark.integration`
- Opik tracing disabled in tests via env var in `tests/conftest.py`

### Eval runs

```bash
uv run python -m evals.run_eval --experiment-name "name"
uv run python -m evals.run_eval --category happy_path
uv run python -m evals.sync_dataset
```

### Commits

One commit per implementation step. Descriptive message: `step N: description`.

## Environment Variables

```bash
OPENAI_API_KEY=sk-...              # Required for LLM calls
COMPOSIO_API_KEY=...               # Required for Gmail/Sheets integration
COMPOSIO_USER_ID=default           # Composio entity ID
COMPOSIO_WEBHOOK_SECRET=...        # Webhook signature verification
SPREADSHEET_ID=...                 # Google Sheets spreadsheet ID
SHEET_NAME=Sheet1                  # Sheet tab name
OPIK_API_KEY=...                   # Opik cloud tracking
OPIK_WORKSPACE=...                 # Opik workspace name
OPIK_PROJECT_NAME=purchase-order-agent  # Opik project name
```

## Current Eval Scores

| Metric | Score | Target |
|---|---|---|
| ClassificationAccuracy | 1.00 | >= 0.95 |
| ExtractionAccuracy | 0.97 | >= 0.85 |
| TrajectoryCorrectness | 1.00 | >= 0.95 |
| ValidationCorrectness | 1.00 | >= 0.85 |
| EmailQuality | 1.00 | >= 0.70 |

## Phase History

- **Phase 1**: Eval framework, core models, service interfaces, stubs, graders, PDF fixtures, 25 scenarios. 105 tests.
- **Phase 2**: Real services (OpenAILLM, TesseractOCR), all 6 nodes, Opik tracing, prompt iteration. 203 tests.
- **Phase 3**: Composio integration (real Gmail/Sheets), FastAPI webhook endpoint, signature verification. 230 tests.
- **Phase 4**: Docker multi-stage build, Railway deployment, webhook dedup, sender email parsing, README. 230 tests.

## Specs

- `phase1_spec.md` — Full Phase 1 specification
- `phase2_spec.md` — Full Phase 2 specification
- `phase3_spec.md` — Full Phase 3 specification
- `phase4_spc.md` — Full Phase 4 specification
