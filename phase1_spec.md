# Phase 1 Implementation Spec: Evaluation Framework + Core Models

## Context

We are building an AI agent that handles inbound procurement workflows (purchase order intake & fulfillment). This spec covers Phase 1: the evaluation framework, core models, and PDF test fixture generator.

**Key principles**:
- **Eval-first**: We build the evaluation system first, then implement the workflow to satisfy it.
- **Test-first (RED → GREEN)**: For every piece of code in `src/`, write the failing test FIRST, then implement. For `evals/`, write grader tests first, then graders. This is non-negotiable.

## Tech Stack

- Python 3.12+
- Package manager: `uv` (ALL dependency management via uv — `uv init`, `uv add`, `uv run pytest`, etc.)
- LangGraph (workflow orchestration)
- Opik (tracing + evaluation dashboard)
- reportlab (PDF generation for test fixtures — matches sample PDF)
- Tesseract + pdf2image (OCR: PDF → images → text. Interface only in Phase 1)
- OpenAI-compatible API for LLM (interface defined in Phase 1, not fully implemented)
- Pydantic v2 for models
- pytest for tests

## Project Structure

```
po-agent/
├── prompts/                          # Prompt store (local YAML files)
│   └── en/                           # Language folder
│       ├── classify.yaml
│       ├── extract.yaml
│       └── notify.yaml
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── purchase_order.py         # PurchaseOrder, ExtractionResult
│   │   ├── workflow_state.py         # POWorkflowState (TypedDict)
│   │   └── webhook.py                # WebhookPayload
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── base.py                   # BaseNode (ABC)
│   │   ├── classify.py               # ClassifyNode (stub in Phase 1)
│   │   ├── extract.py                # ExtractNode (stub in Phase 1)
│   │   ├── validate.py               # ValidateNode (stub in Phase 1)
│   │   ├── track.py                  # TrackNode (stub in Phase 1)
│   │   ├── notify.py                 # NotifyNode (stub in Phase 1)
│   │   └── report.py                 # ReportNode (stub in Phase 1)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ocr/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # OCRService (ABC)
│   │   │   └── tesseract.py          # TesseractOCR (stub)
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # LLMService (ABC)
│   │   │   └── openai.py             # OpenAILLM (stub)
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # ToolManager (ABC)
│   │   │   ├── composio.py           # ComposioToolManager (stub)
│   │   │   └── mock.py               # MockToolManager (FULL implementation)
│   │   └── prompt_store/
│   │       ├── __init__.py
│   │       ├── base.py               # PromptStore (ABC)
│   │       └── local.py              # LocalPromptStore (FULL implementation)
│   ├── config.py                     # AppConfig (Pydantic)
│   ├── builder.py                    # WorkflowBuilder (stub — just wires services)
│   └── workflow.py                   # Graph definition (stub — structure only)
├── evals/
│   ├── __init__.py
│   ├── scenarios/
│   │   ├── happy_path.json
│   │   ├── missing_fields.json
│   │   ├── not_a_po.json
│   │   ├── malformed_pdf.json
│   │   └── ambiguous.json
│   ├── fixtures/                     # Generated PDFs (gitignored, regenerated)
│   ├── graders/
│   │   ├── __init__.py
│   │   ├── classification.py         # ClassificationAccuracy(BaseMetric)
│   │   ├── extraction.py             # ExtractionAccuracy(BaseMetric)
│   │   ├── trajectory.py             # TrajectoryCorrectness(BaseMetric)
│   │   ├── validation.py             # ValidationCorrectness(BaseMetric)
│   │   └── email_quality.py          # EmailQuality(BaseMetric) — LLM-as-judge
│   ├── generate_fixtures.py          # PDF generator script
│   ├── sync_dataset.py               # JSON scenarios → Opik dataset
│   ├── run_eval.py                   # opik.evaluate() runner
│   └── conftest.py                   # pytest fixtures
├── tests/
│   ├── __init__.py
│   ├── test_models.py                # Unit tests for core models
│   ├── test_prompt_store.py          # Unit tests for LocalPromptStore
│   ├── test_mock_tool_manager.py     # Unit tests for MockToolManager
│   └── test_graders.py               # Unit tests for graders
├── config.yaml
├── config.eval.yaml
├── pyproject.toml
├── .gitignore
└── README.md
```

## Detailed Implementation

---

### 1. Core Models (`src/core/`)

#### `purchase_order.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime


class PurchaseOrder(BaseModel):
    """Canonical purchase order data extracted from a PDF."""
    order_id: str
    customer: str
    pickup_location: str
    delivery_location: str
    delivery_datetime: datetime
    driver_name: str
    driver_phone: str


class ExtractionResult(BaseModel):
    """Result of the PDF extraction process."""
    data: PurchaseOrder | None = None
    field_confidences: dict[str, float] = Field(default_factory=dict)
    raw_ocr_text: str = ""
    warnings: list[str] = Field(default_factory=list)
```

#### `workflow_state.py`

```python
from typing import TypedDict


class POWorkflowState(TypedDict, total=False):
    # --- Input (populated from webhook) ---
    email_subject: str
    email_body: str
    email_sender: str
    email_message_id: str
    has_attachment: bool
    pdf_bytes: bytes | None

    # --- Classification ---
    is_valid_po: bool
    po_id: str | None
    classification_reason: str

    # --- Extraction ---
    raw_ocr_text: str
    extracted_data: dict | None          # PurchaseOrder.model_dump()
    field_confidences: dict[str, float]
    extraction_warnings: list[str]

    # --- Validation ---
    validation_errors: list[str]
    missing_fields: list[str]

    # --- Actions & tracking ---
    sheet_row_added: bool
    confirmation_email_sent: bool
    missing_info_email_sent: bool
    actions_log: list[str]
    trajectory: list[str]                # node names visited

    # --- Final ---
    final_status: str                    # "completed" | "missing_info" | "skipped" | "error"
```

#### `webhook.py`

```python
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
```

---

### 2. Service Interfaces (`src/services/`)

All interfaces use ABC (not Protocol). Each service has a `base.py` with the abstract class.

#### `services/ocr/base.py`

```python
from abc import ABC, abstractmethod


class OCRService(ABC):
    @abstractmethod
    def extract_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes. Returns raw text string."""
        ...
```

#### `services/llm/base.py`

```python
from abc import ABC, abstractmethod
from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMService(ABC):
    @abstractmethod
    def structured_output(self, messages: list[dict], response_model: type[T]) -> T:
        """Call LLM and parse response into a Pydantic model."""
        ...

    @abstractmethod
    def generate_text(self, messages: list[dict]) -> str:
        """Call LLM and return raw text response."""
        ...
```

#### `services/tools/base.py`

```python
from abc import ABC, abstractmethod


class ToolManager(ABC):
    @abstractmethod
    def send_email(self, to: str, subject: str, body: str, thread_id: str | None = None) -> dict:
        """Send an email. Returns result dict with at least {"status": "ok"|"error"}."""
        ...

    @abstractmethod
    def append_sheet_row(self, spreadsheet_id: str, values: list[str]) -> dict:
        """Append a row to a Google Sheet. Returns result dict."""
        ...

    @abstractmethod
    def get_email_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Download an email attachment. Returns raw bytes."""
        ...
```

#### `services/prompt_store/base.py`

```python
from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """A single prompt template with its metadata."""
    name: str
    template: str
    description: str = ""
    params: list[str] = Field(default_factory=list)


class PromptStore(ABC):
    """Abstract interface for prompt template storage.

    Templates are organized by category (derived from filename) and prompt name.
    For example, a file `classify.yaml` with a `system` prompt would be accessed
    as `get("classify", "system")`.

    Multi-language support:
    - Templates are organized by language in subfolders (e.g., prompts/en/, prompts/es/)
    - The `language` property returns the current language code
    - The `fallback_language` property returns the fallback language code
    - When a template is not found in the current language, it falls back to the fallback language
    """

    @property
    @abstractmethod
    def language(self) -> str:
        """Current language code (ISO 639-1, e.g., 'en', 'es')."""
        ...

    @property
    @abstractmethod
    def fallback_language(self) -> str:
        """Fallback language code when translation is missing."""
        ...

    @abstractmethod
    def get(self, category: str, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by category and name.

        Args:
            category: Category identifier (typically the YAML filename without extension)
            name: Template identifier within the category (e.g., 'system', 'user')

        Returns:
            PromptTemplate if found, None otherwise
        """
        ...

    @abstractmethod
    def list_categories(self) -> list[str]:
        """List all available categories."""
        ...

    @abstractmethod
    def list_prompts(self, category: str) -> list[str]:
        """List all available prompt names within a category."""
        ...

    @staticmethod
    def render(template: PromptTemplate, params: dict[str, Any]) -> str:
        """Render a template with the given parameters.

        Validates that all required parameters are provided before rendering.

        Args:
            template: The prompt template to render
            params: Dictionary of parameter values

        Returns:
            Rendered template string

        Raises:
            ValueError: If required parameters are missing
        """
        missing = [p for p in template.params if p not in params]
        if missing:
            raise ValueError(
                f"Missing required parameters for template '{template.name}': {missing}"
            )
        return template.template.format(**params)

    def get_and_render(
        self, category: str, name: str, params: Optional[dict[str, Any]] = None
    ) -> str:
        """Get a template and render it in one call.

        Args:
            category: Category identifier
            name: Template identifier within the category
            params: Dictionary of parameter values (defaults to empty dict)

        Returns:
            Rendered template string

        Raises:
            ValueError: If template not found or required parameters missing
        """
        template = self.get(category, name)
        if template is None:
            raise ValueError(f"Prompt template '{category}/{name}' not found")
        return self.render(template, params or {})
```

---

### 3. Service Implementations (Phase 1: MockToolManager + LocalPromptStore)

#### `services/tools/mock.py` — FULL IMPLEMENTATION

```python
from src.services.tools.base import ToolManager


class MockToolManager(ToolManager):
    """Inspectable mock for evaluation. Captures all calls for assertion."""

    def __init__(self):
        self._calls: list[dict] = []

    def send_email(self, to: str, subject: str, body: str, thread_id: str | None = None) -> dict:
        call = {
            "action": "send_email",
            "to": to,
            "subject": subject,
            "body": body,
            "thread_id": thread_id,
        }
        self._calls.append(call)
        return {"status": "ok", "mock": True}

    def append_sheet_row(self, spreadsheet_id: str, values: list[str]) -> dict:
        call = {
            "action": "append_sheet_row",
            "spreadsheet_id": spreadsheet_id,
            "values": values,
        }
        self._calls.append(call)
        return {"status": "ok", "mock": True}

    def get_email_attachment(self, message_id: str, attachment_id: str) -> bytes:
        call = {
            "action": "get_email_attachment",
            "message_id": message_id,
            "attachment_id": attachment_id,
        }
        self._calls.append(call)
        # Return empty bytes — in evals, PDF bytes come from fixtures
        return b""

    # --- Inspection API for graders ---

    @property
    def emails_sent(self) -> list[dict]:
        return [c for c in self._calls if c["action"] == "send_email"]

    @property
    def sheet_rows_added(self) -> list[dict]:
        return [c for c in self._calls if c["action"] == "append_sheet_row"]

    @property
    def all_calls(self) -> list[dict]:
        return list(self._calls)

    def reset(self):
        self._calls.clear()
```

#### `services/prompt_store/local.py` — FULL IMPLEMENTATION

```python
import yaml
from pathlib import Path
from typing import Optional
from src.services.prompt_store.base import PromptStore, PromptTemplate


class LocalPromptStore(PromptStore):
    """Loads prompts from local YAML files organized by language.

    Directory structure:
        prompts/
        ├── en/
        │   ├── classify.yaml      # category: "classify"
        │   ├── extract.yaml       # category: "extract"
        │   └── notify.yaml        # category: "notify"
        └── es/
            └── ...

    YAML format per file (each key is a prompt name within the category):
        system:
            template: |
                You are an email classifier...
            description: System prompt for email classification
            params: []
        user:
            template: |
                Analyze this email:
                Subject: {subject}
                Body: {body}
            description: User prompt template
            params:
                - subject
                - body
    """

    def __init__(self, prompts_dir: str | Path, language: str = "en", fallback_language: str = "en"):
        self._base_dir = Path(prompts_dir)
        self._language = language
        self._fallback_language = fallback_language
        self._cache: dict[str, dict] = {}

        if not self._base_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self._base_dir}")

    @property
    def language(self) -> str:
        return self._language

    @property
    def fallback_language(self) -> str:
        return self._fallback_language

    def get(self, category: str, name: str) -> Optional[PromptTemplate]:
        # Try current language first, then fallback
        for lang in [self._language, self._fallback_language]:
            data = self._load_category(category, lang)
            if data and name in data:
                entry = data[name]
                return PromptTemplate(
                    name=f"{category}.{name}",
                    template=entry["template"],
                    description=entry.get("description", ""),
                    params=entry.get("params", []),
                )
        return None

    def list_categories(self) -> list[str]:
        categories = set()
        for lang in [self._language, self._fallback_language]:
            lang_dir = self._base_dir / lang
            if lang_dir.exists():
                for path in lang_dir.glob("*.yaml"):
                    categories.add(path.stem)
        return sorted(categories)

    def list_prompts(self, category: str) -> list[str]:
        for lang in [self._language, self._fallback_language]:
            data = self._load_category(category, lang)
            if data:
                return list(data.keys())
        return []

    def _load_category(self, category: str, lang: str) -> Optional[dict]:
        cache_key = f"{lang}/{category}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self._base_dir / lang / f"{category}.yaml"
        if not path.exists():
            return None

        with open(path) as f:
            data = yaml.safe_load(f)

        self._cache[cache_key] = data
        return data
```

#### Stub implementations for other services

`services/ocr/tesseract.py`, `services/llm/openai.py`, `services/tools/composio.py` should be created as stubs:

```python
# Example: services/ocr/tesseract.py
from src.services.ocr.base import OCRService


class TesseractOCR(OCRService):
    """Tesseract OCR via image-based extraction.

    Internally: PDF bytes → images (via pdf2image) → Tesseract OCR → text.
    This approach handles both native-text PDFs and scanned documents.
    """
    def extract_text(self, pdf_bytes: bytes) -> str:
        raise NotImplementedError("TesseractOCR will be implemented in Phase 2")
```

Same pattern for `OpenAILLM` and `ComposioToolManager`.

---

### 4. Node Base Class (`src/nodes/base.py`)

```python
from abc import ABC, abstractmethod
from src.core.workflow_state import POWorkflowState


class BaseNode(ABC):
    """Base class for all workflow nodes.

    Subclasses must set `name` as a class variable (str) and implement `__call__`.
    """

    name: str  # Class variable, set by each subclass (e.g. name = "classify")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not getattr(cls, 'name', None) and 'Abstract' not in cls.__name__:
            raise TypeError(f"{cls.__name__} must define a 'name' class variable")

    @abstractmethod
    def __call__(self, state: POWorkflowState) -> dict:
        """Execute node logic. Returns a dict that updates the state."""
        ...
```

Node stubs for Phase 1 — each node should be created as a class inheriting BaseNode with `__call__` raising `NotImplementedError` but with the correct constructor signature showing what services they need:

```python
# Example: src/nodes/classify.py
from src.nodes.base import BaseNode
from src.services.llm.base import LLMService
from src.services.prompt_store.base import PromptStore
from src.core.workflow_state import POWorkflowState


class ClassifyNode(BaseNode):
    name = "classify"

    def __init__(self, llm: LLMService, prompt_store: PromptStore):
        self.llm = llm
        self.prompt_store = prompt_store

    def __call__(self, state: POWorkflowState) -> dict:
        # Usage pattern (for reference, implemented in Phase 2):
        # system = self.prompt_store.get_and_render("classify", "system")
        # user_msg = self.prompt_store.get_and_render("classify", "user", {
        #     "subject": state["email_subject"],
        #     "sender": state["email_sender"],
        #     "body": state["email_body"],
        #     "has_attachment": str(state["has_attachment"]),
        # })
        raise NotImplementedError("ClassifyNode will be implemented in Phase 2")
```

Node constructor signatures:
- `ClassifyNode(llm: LLMService, prompt_store: PromptStore)`
- `ExtractNode(ocr: OCRService, llm: LLMService, prompt_store: PromptStore)`
- `ValidateNode()` — no external dependencies
- `TrackNode(tools: ToolManager, spreadsheet_id: str)`
- `NotifyNode(llm: LLMService, tools: ToolManager, prompt_store: PromptStore)`
- `ReportNode()` — no external dependencies

---

### 5. Prompt Templates (`prompts/`)

Prompts are organized by language, with each YAML file being a category containing multiple named prompts.

**Directory structure:**
```
prompts/
└── en/
    ├── classify.yaml
    ├── extract.yaml
    └── notify.yaml
```

#### `prompts/en/classify.yaml`

```yaml
system:
    template: |
        You are an email classifier for a logistics company called Traza.
        Your job is to determine if an inbound email contains a valid purchase order.

        A valid purchase order email has:
        1. A subject line containing a Purchase Order ID (format: PO-YYYY-NNN or similar)
        2. A PDF attachment

        Respond with a JSON object:
        {
            "is_valid_po": true/false,
            "po_id": "extracted PO ID or null",
            "reason": "brief explanation"
        }
    description: System prompt for email classification
    params: []

user:
    template: |
        Analyze this email:

        Subject: {subject}
        Sender: {sender}
        Body: {body}
        Has PDF attachment: {has_attachment}
    description: User prompt with email details for classification
    params:
        - subject
        - sender
        - body
        - has_attachment
```

#### `prompts/en/extract.yaml`

```yaml
system:
    template: |
        You are a document extraction specialist. Extract structured data from purchase order text.
        The text comes from OCR and may have minor errors.

        Extract ALL of the following fields:
        - order_id: The purchase order ID
        - customer: Customer/company name
        - pickup_location: Full pickup address
        - delivery_location: Full delivery address
        - delivery_datetime: Delivery date and time (ISO 8601 format)
        - driver_name: Assigned truck driver's full name
        - driver_phone: Driver's phone number

        For each field, provide a confidence score between 0.0 and 1.0.
        If a field is not found or ambiguous, set its value to null and confidence to 0.0.

        Respond with a JSON object:
        {
            "data": { ... fields ... },
            "field_confidences": { "order_id": 0.95, ... },
            "warnings": ["list of any issues found"]
        }
    description: System prompt for structured data extraction from OCR text
    params: []

user:
    template: |
        Extract purchase order data from the following OCR text:

        ---
        {ocr_text}
        ---
    description: User prompt with OCR text for extraction
    params:
        - ocr_text
```

#### `prompts/en/notify.yaml`

```yaml
confirmation:
    template: |
        Write a confirmation email for this purchase order:

        Order ID: {order_id}
        Customer: {customer}
        Pickup: {pickup_location}
        Delivery: {delivery_location}
        Delivery Date: {delivery_datetime}
        Driver: {driver_name}

        The email should confirm receipt and that the order is being processed.
    description: Template for generating PO confirmation emails
    params:
        - order_id
        - customer
        - pickup_location
        - delivery_location
        - delivery_datetime
        - driver_name

missing_info:
    template: |
        Write a professional email requesting missing information for purchase order {order_id}.

        The following fields are missing or unclear:
        {missing_fields_description}

        Ask the sender to provide the missing information so we can process the order.
    description: Template for requesting missing PO information
    params:
        - order_id
        - missing_fields_description

system:
    template: |
        You are a professional logistics coordinator at Traza.
        Write email replies to customers about their purchase orders.
        Be professional, concise, and helpful. Use a friendly business tone.
        Include relevant order details in the email.
    description: System prompt for email generation
    params: []
```

---

### 6. Config (`src/config.py`)

```python
from pydantic import BaseModel
from pathlib import Path
import yaml


class AppConfig(BaseModel):
    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None
    llm_api_key: str | None = None  # loaded from env if None

    # OCR
    ocr_engine: str = "tesseract"

    # Tools
    tool_manager: str = "composio"       # "composio" | "mock"
    composio_api_key: str | None = None

    # Prompt store
    prompt_store: str = "local"
    prompts_dir: str = "prompts"
    prompt_language: str = "en"
    prompt_fallback_language: str = "en"

    # Google Sheets
    spreadsheet_id: str = ""

    # Opik
    opik_project: str = "po-workflow"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AppConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @classmethod
    def for_eval(cls) -> "AppConfig":
        """Pre-configured for evaluation: mock tools, real LLM."""
        return cls(
            tool_manager="mock",
            prompt_store="local",
            prompts_dir="prompts",
        )
```

---

### 7. PDF Fixture Generator (`evals/generate_fixtures.py`)

Generate PDFs programmatically using `reportlab` (same lib used for the sample).

The generator should create PDFs that match the structure of the sample:
- Title: "Purchase Order"
- Fields in a table-like layout: Order ID, Customer, Pickup Location, Delivery Location, Delivery Date & Time, Truck Driver, Driver Phone
- Footer text about handling instructions

**Categories of fixtures to generate:**

```python
FIXTURE_CONFIGS = [
    # Happy path — complete POs
    {
        "id": "complete_01",
        "category": "happy_path",
        "fields": {
            "order_id": "PO-2025-001",
            "customer": "Acme Logistics Ltd.",
            "pickup_location": "Warehouse A, 123 Industrial Rd, Madrid",
            "delivery_location": "Retail Hub B, 456 Market St, Barcelona",
            "delivery_datetime": "2025-01-18, 08:00",
            "driver_name": "Juan Pérez",
            "driver_phone": "+34 600 123 456",
        },
    },
    {
        "id": "complete_02",
        "category": "happy_path",
        "fields": {
            "order_id": "PO-2025-042",
            "customer": "Mediterranean Freight Co.",
            "pickup_location": "Port Terminal C, Dock 7, Valencia",
            "delivery_location": "Distribution Center, 89 Logistics Ave, Zaragoza",
            "delivery_datetime": "2025-02-20, 14:30",
            "driver_name": "María García López",
            "driver_phone": "+34 611 234 567",
        },
    },
    # ... generate 3 more happy_path variants

    # Missing fields
    {
        "id": "missing_phone_01",
        "category": "missing_fields",
        "fields": {
            "order_id": "PO-2025-010",
            "customer": "NorthStar Shipping",
            "pickup_location": "Warehouse D, 10 Port Rd, Bilbao",
            "delivery_location": "Store E, 22 Gran Vía, Madrid",
            "delivery_datetime": "2025-03-01, 09:00",
            "driver_name": "Carlos Ruiz",
            "driver_phone": None,  # MISSING
        },
    },
    {
        "id": "missing_driver_01",
        "category": "missing_fields",
        "fields": {
            "order_id": "PO-2025-011",
            "customer": "Iberian Express",
            "pickup_location": "Factory F, Industrial Park, Sevilla",
            "delivery_location": "Warehouse G, 5 Commerce St, Málaga",
            "delivery_datetime": "2025-03-05, 11:00",
            "driver_name": None,   # MISSING
            "driver_phone": None,  # MISSING
        },
    },
    {
        "id": "missing_delivery_date_01",
        "category": "missing_fields",
        "fields": {
            "order_id": "PO-2025-012",
            "customer": "Costa Logistics",
            "pickup_location": "Terminal H, 33 Harbor Blvd, Alicante",
            "delivery_location": "Depot I, 77 Industrial Rd, Murcia",
            "delivery_datetime": None,  # MISSING
            "driver_name": "Ana Martín",
            "driver_phone": "+34 622 345 678",
        },
    },
    # ... 2 more missing field variants

    # Malformed — weird formatting, extra text, scrambled layout
    {
        "id": "malformed_01",
        "category": "malformed_pdf",
        "fields": {
            "order_id": "PO2025-020",        # Missing hyphen after PO
            "customer": "GLOBAL TRANS S.L.",
            "pickup_location": "C/ Industria 45, Pol. Ind. Sur, Granada",
            "delivery_location": "Avda. Constitución 12, 3ºA, Córdoba",
            "delivery_datetime": "18 enero 2025 a las 8h",  # Non-standard format
            "driver_name": "josé antonio lópez",            # Lowercase
            "driver_phone": "600.123.456",                  # Dots instead of spaces
        },
        "layout": "scrambled",  # Different visual layout than standard
    },
    # ... 2 more malformed variants
]
```

The generator script should:
1. Read FIXTURE_CONFIGS
2. For each config, generate a PDF using reportlab
3. Save to `evals/fixtures/{category}/{id}.pdf`
4. Generate a companion `{id}.json` with the expected extraction data (ground truth)

For "not_a_po" scenarios, generate non-PO PDFs (invoices, newsletters, random docs).

For "ambiguous" scenarios, generate PDFs with subtle issues (truncated phone numbers, abbreviated addresses, date without year).

**Target: ~25 PDFs total across all categories.**

---

### 8. Evaluation Scenarios (`evals/scenarios/`)

Each JSON file contains an array of scenarios. Structure:

```json
{
  "scenarios": [
    {
      "id": "happy_path_01",
      "description": "Complete PO with all fields, standard format",
      "category": "happy_path",
      "input": {
        "email_subject": "Purchase Order PO-2025-001",
        "email_body": "Please find attached the purchase order for processing.",
        "email_sender": "orders@acmelogistics.com",
        "email_message_id": "msg_001",
        "has_attachment": true,
        "pdf_fixture": "happy_path/complete_01.pdf"
      },
      "expected": {
        "is_valid_po": true,
        "po_id": "PO-2025-001",
        "extracted_data": {
          "order_id": "PO-2025-001",
          "customer": "Acme Logistics Ltd.",
          "pickup_location": "Warehouse A, 123 Industrial Rd, Madrid",
          "delivery_location": "Retail Hub B, 456 Market St, Barcelona",
          "delivery_datetime": "2025-01-18T08:00:00",
          "driver_name": "Juan Pérez",
          "driver_phone": "+34 600 123 456"
        },
        "missing_fields": [],
        "expected_trajectory": ["classify", "extract", "validate", "track", "notify", "report"],
        "final_status": "completed",
        "expected_sheet_update": true,
        "expected_confirmation_email": true,
        "expected_missing_info_email": false
      }
    }
  ]
}
```

**Scenario categories and counts:**

| File | Category | Count | Description |
|------|----------|-------|-------------|
| happy_path.json | happy_path | 5 | Complete POs, everything works |
| missing_fields.json | missing_fields | 5 | POs with 1-3 missing fields |
| not_a_po.json | not_a_po | 5 | Irrelevant emails (newsletter, spam, general inquiry, invoice, no attachment) |
| malformed_pdf.json | malformed_pdf | 5 | Non-standard formats, typos, weird dates |
| ambiguous.json | ambiguous | 5 | Truncated data, abbreviations, low-confidence fields |

For `not_a_po` scenarios, `pdf_fixture` can be null or point to a non-PO PDF. Expected trajectory is `["classify"]` with `final_status: "skipped"`.

For `missing_fields` scenarios, expected trajectory is `["classify", "extract", "validate", "notify", "report"]` (notify sends a "missing info" email, no track step).

---

### 9. Graders (`evals/graders/`)

All graders extend `opik.evaluation.metrics.BaseMetric`.

#### `graders/classification.py`

```python
from opik.evaluation.metrics import BaseMetric, ScoreResult


class ClassificationAccuracy(BaseMetric):
    """Evaluates whether the email was correctly classified as PO or not."""
    name = "classification_accuracy"

    def score(self, is_valid_po: bool, expected_is_valid_po: bool, **kwargs) -> ScoreResult:
        correct = is_valid_po == expected_is_valid_po
        return ScoreResult(
            value=1.0 if correct else 0.0,
            name=self.name,
            reason=f"Expected {expected_is_valid_po}, got {is_valid_po}",
        )
```

#### `graders/extraction.py`

```python
from opik.evaluation.metrics import BaseMetric, ScoreResult


EXTRACTION_FIELDS = [
    "order_id", "customer", "pickup_location", "delivery_location",
    "delivery_datetime", "driver_name", "driver_phone",
]


class ExtractionAccuracy(BaseMetric):
    """Field-level extraction accuracy. Compares each field independently."""
    name = "extraction_accuracy"

    def score(self, extracted_data: dict | None, expected_extracted_data: dict | None, **kwargs) -> ScoreResult:
        if expected_extracted_data is None:
            # Not a PO scenario — extraction not expected
            return ScoreResult(value=1.0 if extracted_data is None else 0.0, name=self.name)

        if extracted_data is None:
            return ScoreResult(value=0.0, name=self.name, reason="No data extracted")

        correct = 0
        total = len(EXTRACTION_FIELDS)
        mismatches = []

        for field in EXTRACTION_FIELDS:
            expected = expected_extracted_data.get(field)
            actual = extracted_data.get(field)

            if expected is None:
                # Field intentionally missing in ground truth — skip
                total -= 1
                continue

            if self._normalize(actual) == self._normalize(expected):
                correct += 1
            else:
                mismatches.append(f"{field}: expected '{expected}', got '{actual}'")

        score = correct / total if total > 0 else 1.0
        return ScoreResult(
            value=score,
            name=self.name,
            reason=f"{correct}/{total} fields correct. Mismatches: {mismatches}" if mismatches else f"{correct}/{total} fields correct",
        )

    @staticmethod
    def _normalize(value: str | None) -> str | None:
        """Normalize for comparison: lowercase, strip whitespace."""
        if value is None:
            return None
        return str(value).strip().lower()
```

#### `graders/trajectory.py`

```python
from opik.evaluation.metrics import BaseMetric, ScoreResult


class TrajectoryCorrectness(BaseMetric):
    """Checks that the workflow visited the expected sequence of nodes."""
    name = "trajectory_correctness"

    def score(self, trajectory: list[str], expected_trajectory: list[str], **kwargs) -> ScoreResult:
        correct = trajectory == expected_trajectory
        return ScoreResult(
            value=1.0 if correct else 0.0,
            name=self.name,
            reason=f"Expected {expected_trajectory}, got {trajectory}",
        )
```

#### `graders/validation.py`

```python
from opik.evaluation.metrics import BaseMetric, ScoreResult


class ValidationCorrectness(BaseMetric):
    """Checks that missing fields were correctly identified."""
    name = "validation_correctness"

    def score(self, missing_fields: list[str], expected_missing_fields: list[str], **kwargs) -> ScoreResult:
        expected_set = set(expected_missing_fields)
        actual_set = set(missing_fields)

        if not expected_set and not actual_set:
            return ScoreResult(value=1.0, name=self.name, reason="No missing fields expected or found")

        precision = len(expected_set & actual_set) / len(actual_set) if actual_set else (1.0 if not expected_set else 0.0)
        recall = len(expected_set & actual_set) / len(expected_set) if expected_set else 1.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return ScoreResult(
            value=f1,
            name=self.name,
            reason=f"P={precision:.2f} R={recall:.2f} F1={f1:.2f}. Expected: {expected_set}, Got: {actual_set}",
        )
```

#### `graders/email_quality.py`

```python
from opik.evaluation.metrics import BaseMetric, ScoreResult

# NOTE: This is an LLM-as-judge metric. In Phase 1 we define the structure.
# The actual LLM call will be implemented in Phase 2 when LLMService is ready.
# For now, it returns a placeholder score.


class EmailQuality(BaseMetric):
    """LLM-as-judge evaluation of the email response quality.

    Evaluates:
    - Professional tone
    - Mentions PO ID
    - Includes relevant order details
    - No hallucinated information
    - Appropriate next steps
    """
    name = "email_quality"

    def score(self, email_body: str | None, expected_extracted_data: dict | None, final_status: str, **kwargs) -> ScoreResult:
        if final_status == "skipped":
            # No email expected for skipped emails
            if email_body is None:
                return ScoreResult(value=1.0, name=self.name, reason="No email for skipped scenario")
            return ScoreResult(value=0.0, name=self.name, reason="Email sent for skipped scenario")

        if email_body is None:
            return ScoreResult(value=0.0, name=self.name, reason="No email sent")

        # Phase 1: heuristic checks only. LLM-as-judge in Phase 2.
        checks = []
        score = 0.0

        # Check 1: Email is not empty and has reasonable length
        if len(email_body) > 50:
            score += 0.25
            checks.append("sufficient_length")

        # Check 2: Mentions PO ID if available
        po_id = (expected_extracted_data or {}).get("order_id", "")
        if po_id and po_id in email_body:
            score += 0.25
            checks.append("mentions_po_id")

        # Check 3: Contains confirmation language
        confirmation_words = ["confirm", "received", "processing", "recibido", "procesando"]
        if any(w in email_body.lower() for w in confirmation_words):
            score += 0.25
            checks.append("confirmation_language")

        # Check 4: Contains customer name if available
        customer = (expected_extracted_data or {}).get("customer", "")
        if customer and customer.lower() in email_body.lower():
            score += 0.25
            checks.append("mentions_customer")

        return ScoreResult(
            value=score,
            name=self.name,
            reason=f"Checks passed: {checks}",
        )
```

---

### 10. Eval Runner (`evals/run_eval.py`)

```python
"""
Main evaluation runner. Uses opik.evaluate() to run all scenarios
against the workflow and compute metrics.

Usage:
    python -m evals.run_eval
    python -m evals.run_eval --category happy_path
"""
import json
import argparse
from pathlib import Path

from opik import Opik
from opik.evaluation import evaluate

from evals.graders.classification import ClassificationAccuracy
from evals.graders.extraction import ExtractionAccuracy
from evals.graders.trajectory import TrajectoryCorrectness
from evals.graders.validation import ValidationCorrectness
from evals.graders.email_quality import EmailQuality

from src.config import AppConfig
from src.builder import WorkflowBuilder


SCENARIOS_DIR = Path("evals/scenarios")
FIXTURES_DIR = Path("evals/fixtures")


def load_scenarios(category: str | None = None) -> list[dict]:
    """Load scenarios from JSON files, optionally filtered by category."""
    scenarios = []
    for path in SCENARIOS_DIR.glob("*.json"):
        with open(path) as f:
            data = json.load(f)
        for s in data["scenarios"]:
            if category is None or s["category"] == category:
                scenarios.append(s)
    return scenarios


def build_eval_task(workflow, mock_tools):
    """Build the task function that opik.evaluate() will call for each scenario."""

    def eval_task(scenario: dict) -> dict:
        mock_tools.reset()

        # Load PDF fixture if specified
        pdf_bytes = None
        pdf_fixture = scenario["input"].get("pdf_fixture")
        if pdf_fixture:
            pdf_path = FIXTURES_DIR / pdf_fixture
            if pdf_path.exists():
                pdf_bytes = pdf_path.read_bytes()

        # Build workflow input state
        input_state = {
            "email_subject": scenario["input"]["email_subject"],
            "email_body": scenario["input"]["email_body"],
            "email_sender": scenario["input"]["email_sender"],
            "email_message_id": scenario["input"].get("email_message_id", "test"),
            "has_attachment": scenario["input"]["has_attachment"],
            "pdf_bytes": pdf_bytes,
            "actions_log": [],
            "trajectory": [],
        }

        # Run workflow
        result = workflow.invoke(input_state)

        # Extract email body from mock for email quality grading
        emails = mock_tools.emails_sent
        email_body = emails[0]["body"] if emails else None

        # Return dict matching what graders expect
        return {
            "is_valid_po": result.get("is_valid_po", False),
            "extracted_data": result.get("extracted_data"),
            "trajectory": result.get("trajectory", []),
            "missing_fields": result.get("missing_fields", []),
            "final_status": result.get("final_status", "error"),
            "email_body": email_body,
            # Pass through expected values for graders
            "expected_is_valid_po": scenario["expected"]["is_valid_po"],
            "expected_extracted_data": scenario["expected"].get("extracted_data"),
            "expected_trajectory": scenario["expected"]["expected_trajectory"],
            "expected_missing_fields": scenario["expected"].get("missing_fields", []),
        }

    return eval_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, default=None)
    parser.add_argument("--experiment-name", type=str, default=None)
    args = parser.parse_args()

    # Build workflow with mock tools
    config = AppConfig.for_eval()
    builder = WorkflowBuilder(config)
    workflow = builder.build()
    mock_tools = builder.tool_manager  # Access the mock for inspection

    # Load scenarios into Opik dataset
    scenarios = load_scenarios(args.category)
    client = Opik()
    dataset_name = f"po-scenarios-{args.category}" if args.category else "po-scenarios-all"
    dataset = client.get_or_create_dataset(dataset_name)
    dataset.insert(scenarios)

    # Run evaluation
    evaluate(
        dataset=dataset,
        task=build_eval_task(workflow, mock_tools),
        scoring_metrics=[
            ClassificationAccuracy(),
            ExtractionAccuracy(),
            TrajectoryCorrectness(),
            ValidationCorrectness(),
            EmailQuality(),
        ],
        experiment_name=args.experiment_name or f"po-workflow-eval",
        experiment_config={
            "llm_model": config.llm_model,
            "category": args.category or "all",
        },
    )


if __name__ == "__main__":
    main()
```

---

### 11. Sync Dataset Script (`evals/sync_dataset.py`)

Simple utility to push local JSON scenarios to Opik:

```python
"""Sync local JSON scenarios to Opik dataset."""
import json
from pathlib import Path
from opik import Opik

SCENARIOS_DIR = Path("evals/scenarios")


def sync():
    client = Opik()
    all_scenarios = []

    for path in SCENARIOS_DIR.glob("*.json"):
        with open(path) as f:
            data = json.load(f)
        all_scenarios.extend(data["scenarios"])

    dataset = client.get_or_create_dataset("po-scenarios-all")
    dataset.insert(all_scenarios)
    print(f"Synced {len(all_scenarios)} scenarios to Opik dataset 'po-scenarios-all'")

    # Also create per-category datasets
    categories = set(s["category"] for s in all_scenarios)
    for cat in categories:
        cat_scenarios = [s for s in all_scenarios if s["category"] == cat]
        ds = client.get_or_create_dataset(f"po-scenarios-{cat}")
        ds.insert(cat_scenarios)
        print(f"  Synced {len(cat_scenarios)} scenarios to 'po-scenarios-{cat}'")


if __name__ == "__main__":
    sync()
```

---

### 11b. Eval Conftest (`evals/conftest.py`)

Shared pytest fixtures for evaluation tests:

```python
"""Pytest fixtures for evaluation runs."""
import json
from pathlib import Path
import pytest

from src.config import AppConfig
from src.builder import WorkflowBuilder
from src.services.tools.mock import MockToolManager

SCENARIOS_DIR = Path("evals/scenarios")
FIXTURES_DIR = Path("evals/fixtures")


@pytest.fixture
def eval_config() -> AppConfig:
    """AppConfig pre-configured for evaluation."""
    return AppConfig.for_eval()


@pytest.fixture
def mock_tools() -> MockToolManager:
    """Fresh MockToolManager instance, reset between tests."""
    mock = MockToolManager()
    yield mock
    mock.reset()


@pytest.fixture
def eval_workflow(eval_config):
    """Compiled workflow with mock tools for evaluation."""
    builder = WorkflowBuilder(eval_config)
    return builder.build(), builder.tool_manager


def load_scenarios(category: str | None = None) -> list[dict]:
    """Load scenarios from JSON files, optionally filtered by category."""
    scenarios = []
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        for s in data["scenarios"]:
            if category is None or s["category"] == category:
                scenarios.append(s)
    return scenarios


def load_pdf_fixture(fixture_path: str) -> bytes | None:
    """Load a PDF fixture by relative path."""
    if not fixture_path:
        return None
    path = FIXTURES_DIR / fixture_path
    return path.read_bytes() if path.exists() else None
```

#### `config.yaml` (production)

```yaml
llm_provider: openai
llm_model: gpt-4o-mini
ocr_engine: tesseract
tool_manager: composio
prompt_store: local
prompts_dir: prompts
prompt_language: en
prompt_fallback_language: en
spreadsheet_id: ""  # Set via env
opik_project: po-workflow
```

#### `config.eval.yaml`

```yaml
llm_provider: openai
llm_model: gpt-4o-mini
ocr_engine: tesseract
tool_manager: mock
prompt_store: local
prompts_dir: prompts
prompt_language: en
prompt_fallback_language: en
spreadsheet_id: test-sheet
opik_project: po-workflow-eval
```

---

### 13. pyproject.toml

```toml
[project]
name = "po-agent"
version = "0.1.0"
description = "AI agent for purchase order intake and fulfillment"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn>=0.34",
    "pydantic>=2.0",
    "langgraph>=0.2",
    "langchain-core>=0.3",
    "opik>=1.0",
    "pyyaml>=6.0",
    "reportlab>=4.0",
    "pytesseract>=0.3",
    "pdf2image>=1.17",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.8",
]

[tool.pytest.ini_options]
testpaths = ["tests", "evals"]
pythonpath = ["."]

[tool.ruff]
line-length = 120
target-version = "py312"
```

**Note:** Use `uv` for all operations:
```bash
uv init
uv add fastapi uvicorn pydantic langgraph langchain-core opik pyyaml reportlab pytesseract pdf2image httpx
uv add --dev pytest pytest-asyncio ruff
```

---

### 14. Tests (Phase 1)

Tests are described inline in each implementation step above (see Implementation Order).
Each step specifies the exact test cases to write BEFORE the implementation.

**Summary of test files:**

| Test file | Tests for | Step |
|---|---|---|
| `tests/test_models.py` | PurchaseOrder, ExtractionResult, WebhookPayload | 2 |
| `tests/test_mock_tool_manager.py` | MockToolManager call capture and inspection | 4 |
| `tests/test_prompt_store.py` | LocalPromptStore loading, rendering, fallback | 5 |
| `tests/test_nodes.py` | BaseNode ABC, node stubs, constructors | 7 |
| `tests/test_config.py` | AppConfig defaults, from_yaml, for_eval | 9 |
| `tests/test_graders.py` | All 5 Opik BaseMetric graders | 12 |
| `tests/test_builder.py` | WorkflowBuilder service wiring + graph compile | 13 |

---

## Implementation Order (for Claude Code)

**CRITICAL: Test-first (RED → GREEN) approach is mandatory.**

For every implementation step that involves code in `src/`, the workflow is:
1. Write the test → run it → confirm it FAILS (RED)
2. Write the implementation → run the test → confirm it PASSES (GREEN)
3. Commit

For `evals/` code, same principle: write grader tests first, then graders.

Execute in this order. Each step should be a commit.

### Step 1: Project setup
- `uv init` the project
- Create directory structure with all `__init__.py` files
- Create `.gitignore` (include `evals/fixtures/` in gitignore)
- `uv add` all dependencies
- Verify: `uv run python -c "import pydantic; print('ok')"`

### Step 2: Core models (TEST FIRST)
- Write `tests/test_models.py`:
  - Test PurchaseOrder creates with valid data
  - Test PurchaseOrder rejects missing required fields
  - Test ExtractionResult handles None data field
  - Test ExtractionResult default field_confidences is empty dict
  - Test WebhookPayload creates with minimal data
  - Test WebhookPayload defaults (attachment_ids=[], thread_id=None)
- Run tests → all FAIL (RED)
- Implement `src/core/purchase_order.py`, `workflow_state.py`, `webhook.py`
- Run tests → all PASS (GREEN)

### Step 3: Service interfaces
- Create all `base.py` files (OCR, LLM, ToolManager, PromptStore)
- No tests needed — these are abstract classes
- Verify: they import without error

### Step 4: MockToolManager (TEST FIRST)
- Write `tests/test_mock_tool_manager.py`:
  - Test send_email captures call with all args
  - Test append_sheet_row captures call
  - Test get_email_attachment captures call, returns bytes
  - Test emails_sent filters only email calls
  - Test sheet_rows_added filters only sheet calls
  - Test all_calls returns everything
  - Test reset clears all calls
  - Test multiple calls accumulate correctly
- Run tests → all FAIL (RED)
- Implement `src/services/tools/mock.py`
- Run tests → all PASS (GREEN)

### Step 5: LocalPromptStore (TEST FIRST)
- Create test prompt YAML fixtures in `tests/fixtures/prompts/en/`
- Write `tests/test_prompt_store.py`:
  - Test loads prompt by category and name
  - Test returns None for missing prompt
  - Test raises FileNotFoundError for missing directory
  - Test list_categories returns correct list
  - Test list_prompts returns prompt names within category
  - Test render substitutes params correctly
  - Test render raises ValueError for missing required params
  - Test get_and_render combines get + render
  - Test get_and_render raises ValueError for missing template
  - Test language fallback works (request es, fall back to en)
  - Test caching (second get doesn't re-read file)
- Run tests → all FAIL (RED)
- Implement `src/services/prompt_store/local.py`
- Run tests → all PASS (GREEN)

### Step 6: Service stubs
- Create `TesseractOCR`, `OpenAILLM`, `ComposioToolManager` stubs
- Each raises `NotImplementedError`
- Verify: they import without error and inherit from base

### Step 7: Node base + stubs (TEST FIRST)
- Write `tests/test_nodes.py`:
  - Test BaseNode cannot be instantiated (ABC)
  - Test each node stub has correct `name` property
  - Test each node stub raises NotImplementedError on __call__
  - Test each node stub accepts correct constructor args (type hints)
- Run tests → all FAIL (RED)
- Implement `src/nodes/base.py` + all node stubs
- Run tests → all PASS (GREEN)

### Step 8: Prompt templates
- Create `prompts/en/classify.yaml`, `extract.yaml`, `notify.yaml`
- Write a quick test in `tests/test_prompt_store.py` (or extend it) that loads real prompts:
  - Test classify.yaml has 'system' and 'user' prompts
  - Test extract.yaml has 'system' and 'user' prompts
  - Test notify.yaml has 'confirmation', 'missing_info', and 'system' prompts
  - Test user prompts have expected params
- Run → PASS

### Step 9: Config (TEST FIRST)
- Write `tests/test_config.py`:
  - Test AppConfig creates with defaults
  - Test AppConfig.from_yaml loads correctly
  - Test AppConfig.for_eval returns mock tool_manager
- Run tests → FAIL (RED)
- Implement `src/config.py`, create `config.yaml`, `config.eval.yaml`
- Run tests → PASS (GREEN)

### Step 10: PDF fixture generator
- Implement `evals/generate_fixtures.py`
- Run it: `uv run python -m evals.generate_fixtures`
- Verify: PDFs are created in `evals/fixtures/` with correct categories
- Verify: companion JSON ground truth files are created

### Step 11: Evaluation scenarios
- Create all 5 JSON files in `evals/scenarios/` (~25 scenarios total)
- Each scenario references a PDF fixture and has complete expected outputs

### Step 12: Graders (TEST FIRST)
- Write `tests/test_graders.py`:
  - ClassificationAccuracy: true/true → 1.0, true/false → 0.0, false/false → 1.0
  - ExtractionAccuracy: all match → 1.0, half match → ~0.5, None/None → 1.0, None/expected → 0.0
  - ExtractionAccuracy: normalization (whitespace, case) doesn't affect match
  - TrajectoryCorrectness: exact match → 1.0, different order → 0.0, subset → 0.0
  - ValidationCorrectness: empty/empty → 1.0, perfect match → 1.0, partial overlap → F1
  - EmailQuality: long email with PO ID + confirmation + customer → 1.0
  - EmailQuality: empty email → 0.0
  - EmailQuality: skipped scenario with no email → 1.0
- Run tests → all FAIL (RED)
- Implement all 5 graders
- Run tests → all PASS (GREEN)

### Step 13: Builder + workflow skeleton (TEST FIRST)
- Write `tests/test_builder.py`:
  - Test builder with eval config creates MockToolManager as tool_manager
  - Test builder with eval config creates LocalPromptStore as prompt_store
  - Test builder.build() returns a compiled graph without error
  - Test builder exposes tool_manager for inspection in evals
- Run tests → FAIL (RED)
- Implement `src/builder.py`:
  - WorkflowBuilder receives AppConfig
  - Instantiates services based on config (OCR, LLM, ToolManager, PromptStore)
  - Creates node instances injecting services
  - Builds LangGraph StateGraph with nodes and edges
  - Exposes `tool_manager` attribute for eval inspection
- Implement `src/workflow.py`:
  - Defines the graph structure: nodes, edges, conditional routing
  - The graph is fully wired (all edges, conditional logic for skip/missing_info paths)
  - Nodes are the real stub classes (they will raise NotImplementedError when invoked)
  - The graph compiles without error but cannot be invoked end-to-end until Phase 2
- Run tests → PASS (GREEN)

### Step 14: Eval runner + sync + conftest
- Implement `evals/conftest.py` with shared fixtures (eval_config, mock_tools, eval_workflow, load_scenarios, load_pdf_fixture)
- Implement `evals/run_eval.py` and `evals/sync_dataset.py`
- These won't produce meaningful eval results until Phase 2, but should:
  - Load scenarios correctly
  - Load PDF fixtures correctly
  - Build workflow (compiles, even if invoke fails due to stub nodes)
- Verify: `uv run python -m evals.sync_dataset` works (if Opik configured)

### Final verification
- `uv run pytest tests/` → all pass
- `uv run ruff check src/ tests/ evals/` → no errors

## Key Constraints

- Use `uv` for ALL package management (`uv init`, `uv add`, `uv run`)
- All code Python 3.12+
- Pydantic v2
- ABC for interfaces, not Protocol
- **`__init__.py` files must be empty.** Always use full imports: `from src.core.purchase_order import PurchaseOrder`. No re-exports.
- reportlab for PDF generation (matches the sample PDF)
- YAML for prompts, organized by language subfolder
- JSON for scenarios
- **TEST FIRST**: No implementation without a failing test. Write test → RED → implement → GREEN → commit.
- The eval runner won't produce meaningful results until Phase 2 (when nodes are implemented), but it should run without errors on loading/parsing
