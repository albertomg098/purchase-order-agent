# Phase 4 Implementation Spec: Docker + Deploy + README

## Context

Phase 3 delivered Composio integration and FastAPI webhook. The agent works end-to-end: real email → classify → extract → validate → track → notify. 213 unit tests + 19 integration tests passing. All eval thresholds met.

Phase 4 is packaging: containerize, deploy to Railway, connect webhook, and write the README that is the deliverable.

## What's IN Phase 4

1. Dockerfile (FastAPI + Tesseract + Python deps)
2. Railway deployment via GitHub repo
3. Connect Composio trigger webhook to Railway URL
4. Production e2e test (real email → real processing)
5. README.md — the main deliverable document
6. Update CLAUDE.md with final project state

## What's NOT in Phase 4

- No new features or architecture changes
- No new tests (only verify existing pass in container)

---

## Manual Steps Required (USER must do these)

Claude Code cannot do these — the user must complete them at the appropriate points during implementation.

### Before Step 1 (Dockerfile):
- Nothing required. Claude Code can build and test locally.

### Before Step 3 (Railway deployment):
1. **Push repo to GitHub** (if not already done):
   ```bash
   git remote add origin https://github.com/YOUR_USER/po-agent.git
   git push -u origin main
   ```
2. **Create Railway project**:
   - Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
   - Select the `po-agent` repository
   - Railway auto-detects Dockerfile and starts building
3. **Add environment variables in Railway dashboard** (Settings → Variables):
   - `OPENAI_API_KEY` — your OpenAI API key
   - `COMPOSIO_API_KEY` — your Composio API key
   - `COMPOSIO_USER_ID` — your Composio entity ID (email)
   - `SPREADSHEET_ID` — Google Sheet ID for PO tracking
   - `OPIK_API_KEY` — your Opik/Comet API key
   - `OPIK_WORKSPACE` — your Opik workspace name
   - `OPIK_PROJECT_NAME` — set to `po-workflow`
4. **Generate a public domain** in Railway:
   - Go to your service → Settings → Networking → Generate Domain
   - Note the URL (e.g., `https://po-agent-production.up.railway.app`)
5. **Verify deployment**: `curl https://your-railway-url/health`

### Before Step 4 (Connect webhook):
1. **Update Composio trigger webhook URL**:
   - Go to [Composio dashboard](https://app.composio.dev) → Triggers → your Gmail trigger
   - Set callback/webhook URL to `https://your-railway-url/webhook/email`
   - Save the trigger

### After Step 4 (Production e2e test):
1. **Send a real test email** with PO PDF attachment to the connected Gmail
2. **Verify results**:
   - Google Sheet has new row with extracted PO data
   - Confirmation email received by sender
   - Opik dashboard shows complete trace
   - Railway logs show successful processing
3. **Take screenshots** for README (optional but recommended)

---

## Dockerfile

**CRITICAL — Railway PORT variable**: Railway injects a `PORT` environment variable dynamically. The Dockerfile CMD must use **shell form** (not exec/JSON array form) to expand `$PORT` correctly. Using exec form `["uvicorn", ..., "--port", "$PORT"]` will literally pass the string `$PORT` instead of the value.

```dockerfile
# Multi-stage build for smaller image
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first (cache layer)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# --- Runtime stage ---
FROM python:3.12-slim

# Install system dependencies for Tesseract OCR
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-spa \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ src/
COPY prompts/ prompts/
COPY config.yaml .

# Ensure venv is on PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Default port (Railway overrides via $PORT env var)
ENV PORT=8000

# Health check uses the PORT env var
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 8000)}/health')"

# SHELL FORM required — Railway injects PORT dynamically, exec form won't expand $PORT
CMD uvicorn src.api:app --host 0.0.0.0 --port $PORT
```

**Notes:**
- Multi-stage build: builder stage installs deps with uv, runtime stage only has what's needed
- Tesseract + poppler installed at system level (OCR needs these)
- `tesseract-ocr-spa` included for Spanish PO documents
- No `evals/` or `tests/` in the image — production only
- `config.yaml` is copied but env vars override settings at runtime
- Shell form CMD (`CMD uvicorn ...`) not exec form (`CMD ["uvicorn", ...]`) — required for `$PORT` expansion

**CRITICAL — app initialization**: The `src/api.py` uses a factory pattern (`create_app()`). For `uvicorn src.api:app` to work, the module-level `app` must have routes registered. Verify that either:
- (a) `create_app()` is called at module level: `app = create_app()`, OR
- (b) Routes are registered on the module-level `app` object inside `create_app()` AND `create_app()` is called at import time

If Phase 3 implemented it as a factory that returns a new app, the CMD needs to change to use `--factory` flag:
```
CMD uvicorn src.api:create_app --factory --host 0.0.0.0 --port $PORT
```
Claude Code should inspect the actual `src/api.py` and use the appropriate CMD.

### .dockerignore

```
.git
.env
.venv
__pycache__
*.pyc
tests/
evals/
*.md
phase*_spec.md
scripts/
.ruff_cache
```

---

## Railway Deployment

Railway auto-detects the Dockerfile at the project root and uses it to build. No `railway.toml` is needed for basic deployment — Railway handles everything automatically.

**Optional**: If you want healthcheck and restart config in code (instead of dashboard), create a `railway.toml`:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "./Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

**Note**: Config defined in `railway.toml` overrides dashboard settings. If something breaks, check for conflicts between the file and dashboard config. When in doubt, delete `railway.toml` and configure via dashboard only.

### Setup steps
See "Manual Steps Required" section above — user must create the Railway project, add env vars, and generate a domain.

---

## Production E2E Test

Once deployed and webhook connected:

1. Send a real email with PO PDF attachment to the connected Gmail account
2. Wait ~1-2 minutes (trigger interval + processing)
3. Verify:
   - [ ] Google Sheet has new row with extracted PO data
   - [ ] Confirmation email received by sender
   - [ ] Opik dashboard shows complete trace with all spans
   - [ ] Railway logs show successful processing
4. Send a non-PO email (no attachment, random subject)
5. Verify:
   - [ ] No row added to sheet
   - [ ] No reply sent (or appropriate "not a PO" handling)
   - [ ] Opik trace shows classify → report trajectory
6. Take screenshots for README

---

## README.md Structure

The README is the deliverable. It should demonstrate: architecture understanding, evaluation methodology, and production readiness. Claude Code generates the full README by inspecting the actual project.

### Required sections:

**1. Overview (2-3 paragraphs)**
- What the agent does in plain language
- The problem it solves
- Key metrics: 213 unit tests, 19 integration tests, 5 graders, 25 eval scenarios

**2. Architecture**
- High-level diagram (ASCII or Mermaid): email → webhook → classify → extract → validate → track → notify → report
- LangGraph workflow with conditional routing
- Service-oriented design with dependency injection via builder pattern
- List of nodes with their responsibilities (1 line each)

**3. Tech Stack**
- Table format: component → technology → why
- Python 3.12, FastAPI, LangGraph, OpenAI, Tesseract+pdf2image, Composio, Opik, Pydantic, pytest

**4. Evaluation Framework (the most important section)**
- Eval-first approach: framework designed before agent implementation
- 5 graders: ClassificationAccuracy, ExtractionAccuracy, TrajectoryCorrectness, ValidationCorrectness, EmailQuality
- 25 scenarios across 4 categories (happy_path, not_a_po, missing_fields, edge_cases)
- Opik integration for experiment tracking and comparison
- Table of eval scores with targets
- How to run evals: `uv run python -m evals.run_eval --experiment-name "name"`

**5. Key Design Decisions & Tradeoffs**
- Why eval-first (test-first for AI): designed graders and scenarios before implementing nodes
- Why LangGraph over simple pipeline: conditional routing, tracing integration, extensibility
- Why Tesseract over pdfplumber: handles scanned PDFs, demonstrated OCR expertise
- Why Composio direct execution over LLM tool calling: deterministic workflow, nodes decide what to do
- Why structured outputs (native parse()) over Instructor: server-side constraint, no extra dependency
- Why Opik over LangSmith: open-source, provider-agnostic, experiment comparison
- Why async webhook (BackgroundTasks): prevents Composio timeout on long OCR+LLM processing

**6. Project Structure**
- Tree view of `src/`, `evals/`, `tests/`, `prompts/`
- Brief explanation of each top-level directory

**7. Setup & Running**
- Prerequisites: Python 3.12+, uv, Tesseract, API keys
- Local setup steps
- Docker: `docker build -t po-agent .` + `docker run`
- Run tests: `uv run pytest`
- Run evals: `uv run python -m evals.run_eval`

**8. Future Improvements (brief)**
- LLM-as-judge grader (EmailQualityLLM with Opik GEval)
- Re-entry for missing fields (stateful multi-turn)
- Multi-tenant user routing from webhook payload
- Retry logic and idempotency for production reliability
- CI/CD pipeline with eval gates

---

## Implementation Order

### Step 1: Dockerfile + .dockerignore + railway.json
- Create `Dockerfile` (multi-stage as specified above — note shell form CMD for `$PORT`)
- Create `.dockerignore`
- Create `railway.toml` (optional, for healthcheck + restart config in code)
- **CRITICAL**: Verify `src/api.py` has a module-level `app` object that uvicorn can find. The CMD runs `uvicorn src.api:app`. If the app is only created inside `create_app()`, add this to the bottom of `src/api.py`:
  ```python
  app = create_app()
  ```
- Build locally: `docker build -t po-agent .`
- Test locally: `docker run -p 8000:8000 --env-file .env po-agent`
- Verify: `curl http://localhost:8000/health` → `{"status": "ok"}`
- Fix any issues (missing deps, path problems)

### Step 2: Local Docker e2e (optional but recommended)
- With Docker running, send a test webhook payload via curl:
  ```bash
  curl -X POST http://localhost:8000/webhook/email \
    -H "Content-Type: application/json" \
    -d '{"data": {"messageId": "test", "subject": "PO-TEST", "sender": "test@test.com", "snippet": "test", "attachments": []}}'
  ```
- Verify it processes (or fails gracefully for missing attachment)
- Check Docker logs

### Step 3: Railway deployment
- **STOP HERE** — Tell the user to complete the "Before Step 3" manual steps:
  - Push repo to GitHub
  - Create Railway project from GitHub repo
  - Add all env vars in Railway dashboard
  - Generate public domain
- Once user confirms Railway is deployed and health endpoint responds, continue

### Step 4: Connect webhook + production e2e
- **STOP HERE** — Tell the user to complete the "Before Step 4" manual steps:
  - Update Composio trigger webhook URL to Railway URL
- Once user confirms webhook is connected:
  - Tell user to send a real test email with PO PDF attachment
  - Wait and verify results (sheet, reply, Opik trace, Railway logs)

### Step 5: README.md
- Claude Code generates the full README by:
  1. Reading CLAUDE.md for project context
  2. Reading the actual source code structure
  3. Reading eval results from the latest experiment
  4. Following the structure defined above
- Review and adjust manually if needed

### Step 6: Final cleanup
- Update CLAUDE.md with Phase 4 completion
- Verify all files are committed
- Run final check: `uv run pytest tests/unit/` and `uv run ruff check src/ tests/ evals/`
- Tag release: `git tag v1.0.0`

---

## Key Constraints

- Use `uv` for ALL package management
- Dockerfile uses multi-stage build (keep image small)
- No secrets in Docker image or git (env vars only)
- README is written in English
- No new features — only packaging and documentation
- Existing tests must pass: `uv run pytest tests/unit/` → 213+ pass

## Deliverable Checklist

- [ ] `Dockerfile` builds successfully
- [ ] Docker container runs and serves `/health`
- [ ] Railway deployment accessible via public URL
- [ ] Composio webhook connected to Railway URL
- [ ] Production e2e: real email → sheet row + reply + Opik trace
- [ ] `README.md` covers all required sections
- [ ] All tests pass
- [ ] Repo is public on GitHub