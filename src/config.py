from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None
    openai_api_key: str | None = None

    # OCR
    ocr_engine: str = "tesseract"

    # Tools
    tool_manager: str = "composio"  # "composio" | "mock"
    composio_api_key: str | None = None
    composio_user_id: str = "default"
    composio_toolkit_versions: dict = {}

    # Prompt store
    prompt_store: str = "local"
    prompts_dir: str = "prompts"
    prompt_language: str = "en"
    prompt_fallback_language: str = "en"

    # Validation
    confidence_threshold: float = 0.5

    # Google Sheets
    spreadsheet_id: str = ""

    # Opik
    opik_workspace: str = "alberto-martin"
    opik_project: str = "po-workflow"
    opik_api_key: str | None = None

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
