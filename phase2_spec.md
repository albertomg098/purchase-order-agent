# Phase 2 Implementation Spec: Node Implementations + Real Services

## Context

Phase 1 delivered the evaluation framework, core models, service interfaces, and all stubs. Phase 2 implements the real services and workflow nodes so the pipeline runs end-to-end and produces meaningful evaluation scores.

**Key principles** (carried from Phase 1):
- **Test-first (RED → GREEN)**: Write failing test FIRST, then implement. Non-negotiable.
- **Eval-driven iteration**: After implementing each node, run relevant graders to validate.
- **Provider-agnostic tracing**: Opik `@track` on service methods, not on provider SDKs.

## What's IN Phase 2

1. OpenAILLM service (real implementation)
2. TesseractOCR service (real implementation)
3. All 6 node implementations (classify, extract, validate, track, notify, report)
4. Opik tracing (decorators on services + nodes)
5. Prompt iteration (run evals, adjust prompts until scores are acceptable)

## What's NOT in Phase 2

- Composio (real ToolManager) → Phase 3
- FastAPI webhook → Phase 3
- Docker → Phase 4
- README / deliverable packaging → Phase 4
- Re-entry for missing fields (stateful multi-turn) → out of scope

## Entrypoint Architecture

The **entrypoint** is the function that invokes `workflow.invoke()`. It has two responsibilities:
1. Build the input state from external data (email payload, PDF)
2. Create the Opik root trace (via `@opik.track`)

In Phase 2, the entrypoint is the eval runner's `eval_task`. In Phase 3, it will be the FastAPI webhook handler. Both follow the same pattern:

```python
@opik.track(name="po_workflow")
def entrypoint(input_data) -> dict:
    state = build_input_state(input_data)
    result = workflow.invoke(state)
    return result
```

Without `@opik.track` on the entrypoint, node spans become independent traces instead of nested sub-spans. It doesn't break functionality, but you lose the hierarchical view in the Opik dashboard.

## Tech Stack Additions

```bash
uv add openai            # OpenAI Python SDK
uv add pytesseract       # Already in deps from Phase 1
uv add pdf2image         # Already in deps from Phase 1
uv add pillow            # Required by pdf2image
```

**System dependency** (TesseractOCR requires system-level tesseract):
```bash
# macOS
brew install tesseract poppler

# Ubuntu/Debian
sudo apt-get install tesseract-ocr poppler-utils
```

---

## SDK Reference (for Claude Code)

### OpenAI Python SDK — Structured Outputs

The key API for our use case is `client.beta.chat.completions.parse()` which returns a Pydantic model directly:

```python
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()  # reads OPENAI_API_KEY from env

class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

completion = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Extract the event information."},
        {"role": "user", "content": "Alice and Bob are going to a science fair on Friday."},
    ],
    response_format=CalendarEvent,
)

event = completion.choices[0].message.parsed  # Already a CalendarEvent instance
```

**Important notes:**
- `response_format` accepts a Pydantic BaseModel class directly
- `.parsed` returns the typed Pydantic instance (or None if refusal)
- For plain text generation (no structured output), use regular `client.chat.completions.create()` without response_format
- The `base_url` parameter allows pointing to OpenRouter or other OpenAI-compatible APIs

### Opik Python SDK — Tracing

**`@opik.track` decorator** — Creates a span for any function call. Automatically nests when called within another tracked function:

```python
import opik

@opik.track(name="my_function")
def my_function(input: str) -> str:
    return "result"

# Nested spans:
@opik.track(name="outer")
def outer():
    return inner()  # inner span is nested inside outer

@opik.track(name="inner")
def inner():
    return "result"
```

**Configuration via environment variables:**
```bash
OPIK_API_KEY=your_api_key_here
OPIK_WORKSPACE=your_workspace_name
OPIK_PROJECT_NAME=po-workflow
# Optional for cloud:
OPIK_URL_OVERRIDE=https://www.comet.com/opik/api
```

**`opik.evaluate()`** — Runs task function against dataset with scoring metrics:

```python
from opik import Opik
from opik.evaluation import evaluate

client = Opik()
dataset = client.get_or_create_dataset("my-dataset")
dataset.insert([{"input": "test", "expected": "result"}])

def eval_task(item: dict) -> dict:
    result = my_function(item["input"])
    return {"output": result, "expected": item["expected"]}

evaluate(
    dataset=dataset,
    task=eval_task,
    scoring_metrics=[MyMetric()],
    experiment_name="experiment-v1",
    experiment_config={"model": "gpt-4o-mini"},
    trial_count=3,  # Handles non-determinism
)
```

**Key: `@opik.track` is provider-agnostic.** It works on ANY Python function. We use it on our service methods (LLMService, OCRService) and on node `__call__` methods. This avoids coupling tracing to any specific LLM provider.

---

## Architecture Decisions

### Tracing Strategy (Two Layers)

**Root trace**: Each workflow invocation needs a root trace. The eval runner's `eval_task` function and the future webhook handler get `@opik.track(name="po_workflow")`. This creates the top-level trace; all node spans nest inside automatically.

```
Trace: po_workflow               ← @opik.track on eval_task / webhook handler
├── Span: classify_node          ← @opik.track on ClassifyNode.__call__
│   └── Span: llm_structured     ← @opik.track on OpenAILLM.structured_output
├── Span: extract_node
│   ├── Span: ocr_extract        ← @opik.track on TesseractOCR.extract_text
│   └── Span: llm_structured     ← @opik.track on OpenAILLM.structured_output
├── Span: validate_node          ← @opik.track (no sub-spans, pure logic)
├── Span: track_node             ← @opik.track
├── Span: notify_node
│   └── Span: llm_generate       ← @opik.track on OpenAILLM.generate_text
└── Span: report_node            ← @opik.track
```

**Implementation**: `@opik.track` on `__call__` in each node, and on `structured_output`, `generate_text`, and `extract_text` in services. Opik auto-nests when a tracked function calls another tracked function.

**Disabling tracing for unit tests**: Opik's `@opik.track` decorator is always present in the code (no conditional logic). To prevent sending traces during unit tests, set the environment variable in `tests/conftest.py`:

```python
# tests/conftest.py
import os

# Disable Opik tracing during tests to avoid sending data and needing API keys
os.environ.setdefault("OPIK_TRACK_DISABLE", "true")
```

**Note**: Verify the exact env var name from Opik docs at implementation time. If Opik doesn't support a disable flag, the fallback approach is: set `OPIK_API_KEY` to empty and let Opik fail silently (which it already does based on Phase 1 test output).

### LLMService Implementation

```python
from openai import OpenAI
from pydantic import BaseModel
from typing import TypeVar
import opik

from src.services.llm.base import LLMService

T = TypeVar("T", bound=BaseModel)


class OpenAILLM(LLMService):
    """OpenAI-compatible LLM service with structured output support."""

    def __init__(self, model: str = "gpt-4o-mini", base_url: str | None = None, api_key: str | None = None):
        self._model = model
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    @opik.track(name="llm_structured_output")
    def structured_output(self, messages: list[dict], response_model: type[T]) -> T:
        completion = self._client.beta.chat.completions.parse(
            model=self._model,
            messages=messages,
            response_format=response_model,
        )
        result = completion.choices[0].message.parsed
        if result is None:
            raise ValueError(f"LLM refused to respond or failed to parse into {response_model.__name__}")
        return result

    @opik.track(name="llm_generate_text")
    def generate_text(self, messages: list[dict]) -> str:
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        return completion.choices[0].message.content or ""
```

### OCRService Implementation

```python
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import opik

from src.services.ocr.base import OCRService


class TesseractOCR(OCRService):
    """Tesseract OCR via image-based extraction.
    
    PDF bytes → images (via pdf2image/poppler) → Tesseract OCR → concatenated text.
    """

    def __init__(self, lang: str = "eng", dpi: int = 300):
        self._lang = lang
        self._dpi = dpi

    @opik.track(name="ocr_extract_text")
    def extract_text(self, pdf_bytes: bytes) -> str:
        images: list[Image.Image] = convert_from_bytes(pdf_bytes, dpi=self._dpi)
        texts = []
        for img in images:
            text = pytesseract.image_to_string(img, lang=self._lang)
            texts.append(text)
        return "\n".join(texts).strip()
```

---

## Error Handling Pattern

Every node wraps its logic in try/except. On error, the node sets `final_status: "error"` and `error_message` in the state, and the workflow routes to ReportNode.

```python
# Pattern for all nodes (example: ClassifyNode)
@opik.track(name="classify_node")
def __call__(self, state: POWorkflowState) -> dict:
    try:
        # ... node logic ...
        return {
            "is_valid_po": result.is_valid_po,
            "po_id": result.po_id,
            "trajectory": state.get("trajectory", []) + ["classify"],
        }
    except Exception as e:
        return {
            "final_status": "error",
            "error_message": f"ClassifyNode failed: {str(e)}",
            "trajectory": state.get("trajectory", []) + ["classify"],
        }
```

**Downstream nodes check for error**: Each node checks `state.get("final_status") == "error"` at the top and returns immediately if true, passing the state through unchanged (only appending to trajectory).

```python
# Guard at top of each node
if state.get("final_status") == "error":
    return {"trajectory": state.get("trajectory", []) + [self.name]}
```

This ensures the error propagates through the pipeline to ReportNode, which logs the final error status.

---

## Node Implementations

### ClassifyNode

**Input from state**: `email_subject`, `email_body`, `email_sender`, `has_attachment`
**Output to state**: `is_valid_po`, `po_id`, `classification_reason`
**Services**: LLMService, PromptStore
**Constructor**: `ClassifyNode(llm: LLMService, prompt_store: PromptStore)`

**Logic**:
1. Get system prompt: `prompt_store.get_and_render("classify", "system")`
2. Get user prompt: `prompt_store.get_and_render("classify", "user", {subject, sender, body, has_attachment})`
3. Build messages list (this is the pattern ALL nodes follow):
   ```python
   messages = [
       {"role": "system", "content": system_prompt},
       {"role": "user", "content": user_prompt},
   ]
   ```
4. Define a Pydantic response model:
   ```python
   class ClassificationResult(BaseModel):
       is_valid_po: bool
       po_id: str | None = None
       reason: str
   ```
5. Call `llm.structured_output(messages, ClassificationResult)`
6. Return dict updating state with results
7. Append "classify" to trajectory

**Note on PromptStore → messages**: `get_and_render()` returns a rendered string. Nodes are responsible for assembling the `messages` list. This keeps PromptStore simple (template rendering) and gives nodes control over the message structure.

### ExtractNode

**Input from state**: `pdf_bytes`, `is_valid_po`
**Output to state**: `raw_ocr_text`, `extracted_data`, `field_confidences`, `extraction_warnings`
**Services**: OCRService, LLMService, PromptStore
**Constructor**: `ExtractNode(ocr: OCRService, llm: LLMService, prompt_store: PromptStore)`

**Logic**:
1. If not `is_valid_po`, skip (return empty)
2. Run OCR: `raw_text = ocr.extract_text(pdf_bytes)`
3. Get prompts from store
4. Define response model matching ExtractionResult structure:
   ```python
   class LLMExtractionResponse(BaseModel):
       data: dict[str, str | None]
       field_confidences: dict[str, float]
       warnings: list[str]
   ```
5. Call `llm.structured_output(messages, LLMExtractionResponse)`
6. Map response into state fields
7. Append "extract" to trajectory

### ValidateNode

**Input from state**: `extracted_data`, `field_confidences`
**Output to state**: `validation_errors`, `missing_fields`
**Services**: None (pure logic)
**Constructor**: `ValidateNode(confidence_threshold: float = 0.5)`

**Note**: Phase 1 spec defined `ValidateNode()` with no args. This is a breaking change — update the Phase 1 node stub to accept `confidence_threshold` in the constructor. Update `tests/unit/test_nodes.py` accordingly.

**Logic**:
1. Check each of the 7 required fields in `extracted_data`
2. A field is "missing" if it's None, empty string, or has confidence < threshold (e.g., 0.5)
3. Build `missing_fields` list and `validation_errors` list
4. If missing_fields is empty → status stays on track for "completed"
5. If missing_fields not empty → status will become "missing_info"
6. Append "validate" to trajectory

**Confidence threshold**: Configurable, default 0.5. Add to AppConfig as `confidence_threshold: float = 0.5`.

### TrackNode

**Input from state**: `extracted_data`, `po_id`, `is_valid_po`
**Output to state**: `sheet_row_added`
**Services**: ToolManager
**Constructor**: `TrackNode(tools: ToolManager, spreadsheet_id: str)`

**Logic**:
1. If not `is_valid_po`, skip
2. Determine row status: `"complete"` if `missing_fields` is empty, `"pending_info"` otherwise
3. Build row values from extracted_data: `[po_id, customer, pickup, delivery, date, driver, phone, row_status]`
4. Call `tools.append_sheet_row(spreadsheet_id, values)`
5. Record result in state
6. Append "track" to trajectory

### NotifyNode

**Input from state**: `extracted_data`, `missing_fields`, `email_sender`, `po_id`, `is_valid_po`
**Output to state**: `emails_sent`
**Services**: LLMService, ToolManager, PromptStore
**Constructor**: `NotifyNode(llm: LLMService, tools: ToolManager, prompt_store: PromptStore)`

**Logic**:
1. If not `is_valid_po`, skip (no notification for non-PO emails)
2. Choose prompt based on missing_fields:
   - No missing fields → use `notify/confirmation` template
   - Has missing fields → use `notify/missing_info` template
3. Get system prompt: `prompt_store.get_and_render("notify", "system")`
4. Get user prompt with appropriate template and params
5. Call `llm.generate_text(messages)` to generate email body
6. Call `tools.send_email(to=email_sender, subject=..., body=generated_email)`
7. Record in state
8. Append "notify" to trajectory

### ReportNode

**Input from state**: All accumulated state
**Output to state**: `final_status`
**Services**: None (pure logic)
**Constructor**: `ReportNode()`

**Why this node exists**: It's a single "finalizer" that runs on ALL paths (both valid PO and non-PO). This gives us one canonical place to determine final_status, ensuring consistency and making the trajectory always end with "report" regardless of the path taken.

**Logic**:
1. Determine final status based on state:
   - `error_message` is set → `"error"`
   - Not a valid PO → `"skipped"`
   - Valid PO, no missing fields → `"completed"`
   - Valid PO, has missing fields → `"missing_info"`
2. Append "report" to trajectory
3. Return final state update

**Graph routing**: Both paths converge here:
```
classify → [valid PO]   → extract → validate → track → notify → report → END
classify → [not valid]  → report → END
```

---

## Workflow Graph (LangGraph)

```python
from langgraph.graph import StateGraph, END
from src.core.workflow_state import POWorkflowState


def should_continue_after_classify(state: POWorkflowState) -> str:
    """Route based on classification result."""
    if state.get("is_valid_po"):
        return "extract"
    return "report"  # Skip to report for non-PO emails


def build_graph(nodes: dict) -> StateGraph:
    graph = StateGraph(POWorkflowState)

    # Add nodes
    graph.add_node("classify", nodes["classify"])
    graph.add_node("extract", nodes["extract"])
    graph.add_node("validate", nodes["validate"])
    graph.add_node("track", nodes["track"])
    graph.add_node("notify", nodes["notify"])
    graph.add_node("report", nodes["report"])

    # Set entry point
    graph.set_entry_point("classify")

    # Add edges
    graph.add_conditional_edges("classify", should_continue_after_classify)
    graph.add_edge("extract", "validate")
    graph.add_edge("validate", "track")
    graph.add_edge("track", "notify")
    graph.add_edge("notify", "report")
    graph.add_edge("report", END)

    return graph.compile()
```

**Expected trajectories:**
- Happy path: `["classify", "extract", "validate", "track", "notify", "report"]`
- Not a PO: `["classify", "report"]`
- Missing fields: `["classify", "extract", "validate", "track", "notify", "report"]` (same graph path, different final_status)

**Why missing_fields has the same path**: The routing is the same. The difference is behavioral — NotifyNode reads `missing_fields` from state and selects the appropriate email template (`notify/confirmation` vs `notify/missing_info`). TrackNode logs the PO with `status` reflecting the validation result. ReportNode sets `final_status` to `"missing_info"` instead of `"completed"`.

---

## LLM Response Models (`src/core/llm_responses.py`)

These are Pydantic models that define the expected structured output from the LLM. They live in `src/core/` (not inside nodes) because they're part of the domain contract.

```python
from pydantic import BaseModel


class ClassificationResult(BaseModel):
    """LLM response for email classification."""
    is_valid_po: bool
    po_id: str | None = None
    reason: str


class LLMExtractionResponse(BaseModel):
    """LLM response for PO data extraction."""
    data: dict[str, str | None]
    field_confidences: dict[str, float]
    warnings: list[str] = []
```

---

## Testing Strategy

### Test Mocks (`tests/conftest.py` or `tests/mocks.py`)

Shared mocks for unit testing. These live in `tests/` and are available to all test files.

```python
from src.services.llm.base import LLMService
from src.services.ocr.base import OCRService


class MockLLM(LLMService):
    """Returns pre-configured responses for testing."""
    def __init__(self, structured_response=None, text_response="", should_raise: Exception | None = None):
        self._structured = structured_response
        self._text = text_response
        self._should_raise = should_raise

    def structured_output(self, messages, response_model):
        if self._should_raise:
            raise self._should_raise
        return self._structured

    def generate_text(self, messages):
        if self._should_raise:
            raise self._should_raise
        return self._text


class MockOCR(OCRService):
    """Returns pre-configured OCR text for testing."""
    def __init__(self, text: str = "", should_raise: Exception | None = None):
        self._text = text
        self._should_raise = should_raise

    def extract_text(self, pdf_bytes: bytes) -> str:
        if self._should_raise:
            raise self._should_raise
        return self._text
```

### Unit Tests (with mocks)

Each node gets unit tests with MockLLM, MockOCR, and MockToolManager (from Phase 1). No real LLM or OCR calls.

**Tests per node:**
- ClassifyNode: valid PO detected, non-PO detected, missing attachment
- ExtractNode: all fields extracted, partial extraction, skips when not valid PO
- ValidateNode: no missing fields, some missing fields, low confidence fields
- TrackNode: appends correct row, skips when not valid PO
- NotifyNode: sends confirmation email, sends missing-info email, skips non-PO
- ReportNode: completed status, missing_info status, skipped status, error status

### Integration Tests (real LLM, mocked tools)

Run actual LLM calls against a few scenarios to verify prompt effectiveness:

```python
# tests/integration/test_classify_llm.py
@pytest.mark.integration
def test_classify_real_llm_happy_path():
    """Real LLM call to verify classify prompt works."""
    llm = OpenAILLM(model="gpt-4o-mini")
    prompt_store = LocalPromptStore("prompts", language="en")
    node = ClassifyNode(llm=llm, prompt_store=prompt_store)
    # ... build state from a happy_path scenario
    # ... assert is_valid_po is True
```

Mark with `@pytest.mark.integration` so they can be skipped in CI without API keys.

### Eval Runs

After all nodes are implemented, the eval runner from Phase 1 becomes functional:

```bash
# Run all scenarios
uv run python -m evals.run_eval

# Run specific category
uv run python -m evals.run_eval --category happy_path

# Run with experiment name for comparison
uv run python -m evals.run_eval --experiment-name "v1-gpt4o-mini"
```

---

## Builder Updates

Update `WorkflowBuilder` to instantiate services **based on config values**:

```python
class WorkflowBuilder:
    def __init__(self, config: AppConfig):
        self.config = config
        self._init_services()

    def _init_services(self):
        # LLM — config-driven
        if self.config.llm_provider == "openai":
            self.llm = OpenAILLM(
                model=self.config.llm_model,
                api_key=self.config.openai_api_key,
            )
        else:
            raise ValueError(f"Unknown LLM provider: {self.config.llm_provider}")

        # OCR — config-driven
        if self.config.ocr_engine == "tesseract":
            self.ocr = TesseractOCR()
        else:
            raise ValueError(f"Unknown OCR engine: {self.config.ocr_engine}")

        # Tools — config-driven
        if self.config.tool_manager == "mock":
            self.tool_manager = MockToolManager()
        elif self.config.tool_manager == "composio":
            raise NotImplementedError("ComposioToolManager is Phase 3")
        else:
            raise ValueError(f"Unknown tool manager: {self.config.tool_manager}")

        # Prompts — config-driven
        self.prompt_store = LocalPromptStore(
            self.config.prompts_dir,
            language=self.config.prompt_language,
            fallback_language=self.config.prompt_fallback_language,
        )

    def build(self):
        nodes = {
            "classify": ClassifyNode(self.llm, self.prompt_store),
            "extract": ExtractNode(self.ocr, self.llm, self.prompt_store),
            "validate": ValidateNode(self.config.confidence_threshold),
            "track": TrackNode(self.tool_manager, self.config.spreadsheet_id),
            "notify": NotifyNode(self.llm, self.tool_manager, self.prompt_store),
            "report": ReportNode(),
        }
        return build_graph(nodes)
```

---

## Config Additions

Add to `AppConfig`:

```python
# New fields for Phase 2
openai_api_key: str | None = None           # from OPENAI_API_KEY env
opik_api_key: str | None = None             # from OPIK_API_KEY env
opik_workspace: str | None = None           # from OPIK_WORKSPACE env
confidence_threshold: float = 0.5           # for ValidateNode
```

Add to `POWorkflowState` (if not already present from Phase 1):

```python
# Error handling fields
error_message: str | None      # Set by any node on failure
```

Add to `.env.example`:

```bash
OPENAI_API_KEY=sk-...
OPIK_API_KEY=
OPIK_WORKSPACE=
OPIK_PROJECT_NAME=po-workflow
```

---

## Implementation Order

**CRITICAL: Test-first (RED → GREEN) approach is mandatory.**

### Step 1: Config + model updates
- Add `openai_api_key`, `opik_api_key`, `opik_workspace`, `confidence_threshold` to AppConfig
- Create `.env.example` and `.env` (gitignored)
- Create `src/core/llm_responses.py` with `ClassificationResult` and `LLMExtractionResponse`
- Create `tests/mocks.py` with `MockLLM` and `MockOCR` (shared test mocks)
- Add `error_message` field to `POWorkflowState` (TypedDict)
- Update `tests/unit/test_config.py` with new fields
- Update `tests/unit/test_models.py` to test new LLM response models
- Run → PASS (quick fix, minimal)

### Step 2: OpenAILLM (TEST FIRST)
- Write `tests/unit/test_openai_llm.py`:
  - Test constructor accepts model, base_url, api_key
  - Test structured_output calls client correctly (mock OpenAI client)
  - Test structured_output raises ValueError on None parsed result
  - Test generate_text calls client correctly (mock OpenAI client)
  - Test generate_text returns empty string on None content
- Run tests → FAIL (RED)
- Implement `src/services/llm/openai_llm.py`
- Run tests → PASS (GREEN)

### Step 3: TesseractOCR (TEST FIRST)
- Write `tests/unit/test_tesseract_ocr.py`:
  - Test constructor accepts lang and dpi
  - Test extract_text calls pdf2image and pytesseract (mock both)
  - Test extract_text concatenates text from multiple pages
  - Test extract_text strips whitespace
  - Test extract_text handles empty PDF (no pages)
- Run tests → FAIL (RED)
- Implement `src/services/ocr/tesseract.py`
- Run tests → PASS (GREEN)

### Step 4: ClassifyNode (TEST FIRST)
- Write `tests/unit/test_classify_node.py`:
  - Test valid PO email → is_valid_po=True, po_id extracted
  - Test non-PO email → is_valid_po=False
  - Test email without attachment → is_valid_po=False
  - Test trajectory updated with "classify"
  - Test LLM error → final_status="error", error_message set
  - Test error guard: if state already has final_status="error", node passes through
  - Use MockLLM that returns pre-configured ClassificationResult
- Run tests → FAIL (RED)
- Implement `src/nodes/classify.py`
- Run tests → PASS (GREEN)

### Step 5: ExtractNode (TEST FIRST)
- Write `tests/unit/test_extract_node.py`:
  - Test full extraction with all 7 fields
  - Test partial extraction (some fields None)
  - Test skips when is_valid_po=False
  - Test OCR text stored in state as raw_ocr_text
  - Test trajectory updated with "extract"
  - Test OCR error → final_status="error"
  - Test LLM error → final_status="error"
  - Test error guard: passes through if already errored
  - Use MockLLM + MockOCR
- Run tests → FAIL (RED)
- Implement `src/nodes/extract.py`
- Run tests → PASS (GREEN)

### Step 6: ValidateNode (TEST FIRST)
- Write `tests/unit/test_validate_node.py`:
  - Test no missing fields → empty missing_fields list
  - Test None field → appears in missing_fields
  - Test empty string field → appears in missing_fields
  - Test low confidence field (< threshold) → appears in missing_fields
  - Test high confidence field (>= threshold) → not in missing_fields
  - Test trajectory updated with "validate"
  - No mocks needed (pure logic)
- Run tests → FAIL (RED)
- Implement `src/nodes/validate.py`
- Run tests → PASS (GREEN)

### Step 7: TrackNode (TEST FIRST)
- Write `tests/unit/test_track_node.py`:
  - Test appends correct row values to sheet
  - Test skips when is_valid_po=False
  - Test trajectory updated with "track"
  - Use MockToolManager (from Phase 1)
- Run tests → FAIL (RED)
- Implement `src/nodes/track.py`
- Run tests → PASS (GREEN)

### Step 8: NotifyNode (TEST FIRST)
- Write `tests/unit/test_notify_node.py`:
  - Test sends confirmation email when no missing fields
  - Test sends missing-info email when fields are missing
  - Test skips when is_valid_po=False
  - Test email sent to original sender
  - Test trajectory updated with "notify"
  - Use MockLLM + MockToolManager
- Run tests → FAIL (RED)
- Implement `src/nodes/notify.py`
- Run tests → PASS (GREEN)

### Step 9: ReportNode (TEST FIRST)
- Write `tests/unit/test_report_node.py`:
  - Test completed status (valid PO, no missing fields)
  - Test missing_info status (valid PO, has missing fields)
  - Test skipped status (not a valid PO)
  - Test error status (error_message is set in state)
  - Test error takes precedence over other conditions
  - Test trajectory updated with "report"
- Run tests → FAIL (RED)
- Implement `src/nodes/report.py`
- Run tests → PASS (GREEN)

### Step 10: Workflow graph + Builder update
- Update `src/workflow.py` with full graph (conditional edges, routing — both paths converge on report)
- Update `src/builder.py` to instantiate services based on config (config-driven)
- Update Phase 1 ValidateNode stub to accept `confidence_threshold` in constructor
- Update `tests/unit/test_nodes.py` for new ValidateNode constructor
- Update `tests/integration/test_builder.py`:
  - Test builder with eval config creates full workflow
  - Test builder with `llm_provider="openai"` creates OpenAILLM
  - Test builder with `ocr_engine="tesseract"` creates TesseractOCR
  - Test builder with `tool_manager="mock"` creates MockToolManager
  - Test builder with unknown provider raises ValueError
  - Test workflow compiles with all real nodes
- Run tests → PASS

### Step 11: Opik tracing
- Add `@opik.track` decorators to:
  - `OpenAILLM.structured_output` and `.generate_text`
  - `TesseractOCR.extract_text`
  - Each node's `__call__` method
- Add `@opik.track(name="po_workflow")` to the `eval_task` function in `evals/run_eval.py` (root trace)
- Add Opik disable env var to `tests/conftest.py`: `os.environ.setdefault("OPIK_TRACK_DISABLE", "true")`
  - At implementation time, verify the exact env var name from Opik docs
  - Fallback: leave `OPIK_API_KEY` unset and let Opik fail silently
- Verify existing unit tests still pass (tracing decorators should be transparent when disabled)
- Manual verification: run one scenario with real API keys, check Opik dashboard shows hierarchical traces

### Step 12: Integration tests with real LLM
- Write `tests/integration/test_classify_llm.py`:
  - Real LLM call with happy_path scenario → is_valid_po=True
  - Real LLM call with not_a_po scenario → is_valid_po=False
- Write `tests/integration/test_extract_llm.py`:
  - Real LLM + real OCR on a happy_path PDF fixture
  - Verify extracted fields match expected
- Mark all with `@pytest.mark.integration`
- Add pytest config: `uv run pytest tests/integration/ -m integration`

### Step 13: End-to-end eval run
- Run: `uv run python -m evals.run_eval --category happy_path --experiment-name "phase2-v1"`
- Review scores in Opik dashboard
- Identify failing scenarios

### Step 14: Prompt iteration
- Based on eval results, adjust prompts in `prompts/en/*.yaml`
- Re-run evals: `uv run python -m evals.run_eval --experiment-name "phase2-v2"`
- Compare experiments in Opik dashboard
- Repeat until scores are acceptable:
  - ClassificationAccuracy ≥ 0.95
  - ExtractionAccuracy ≥ 0.85
  - TrajectoryCorrectness ≥ 0.95
  - ValidationCorrectness ≥ 0.85
  - EmailQuality ≥ 0.70

### Final verification
- `uv run pytest tests/unit/` → all pass
- `uv run pytest tests/integration/ -m integration` → all pass (requires API keys)
- `uv run ruff check src/ tests/ evals/` → no errors
- Opik dashboard shows traces and experiment results

---

## Key Constraints

- Use `uv` for ALL package management
- **TEST FIRST**: No implementation without a failing test
- **`__init__.py` files must be empty.** Always use full imports.
- `@opik.track` on service methods and node `__call__`, NOT on provider SDKs
- MockToolManager continues to be used (no real Composio until Phase 3)
- Integration tests require `OPENAI_API_KEY` and are marked with `@pytest.mark.integration`
- Opik tracing disabled in unit tests (env var or conftest)

## Test Summary

| Test file | Tests for | Step |
|---|---|---|
| `tests/unit/test_openai_llm.py` | OpenAILLM structured output and text generation | 2 |
| `tests/unit/test_tesseract_ocr.py` | TesseractOCR PDF → image → text pipeline | 3 |
| `tests/unit/test_classify_node.py` | ClassifyNode classification logic | 4 |
| `tests/unit/test_extract_node.py` | ExtractNode OCR + LLM extraction | 5 |
| `tests/unit/test_validate_node.py` | ValidateNode field validation logic | 6 |
| `tests/unit/test_track_node.py` | TrackNode sheet row appending | 7 |
| `tests/unit/test_notify_node.py` | NotifyNode email generation | 8 |
| `tests/unit/test_report_node.py` | ReportNode final status determination | 9 |
| `tests/integration/test_builder.py` | Builder with real services (updated) | 10 |
| `tests/integration/test_classify_llm.py` | Real LLM classification | 12 |
| `tests/integration/test_extract_llm.py` | Real LLM + OCR extraction | 12 |
