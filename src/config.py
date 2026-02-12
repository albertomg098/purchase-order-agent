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
