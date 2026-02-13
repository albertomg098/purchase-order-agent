"""Unit tests for AppConfig."""
from pathlib import Path

import pytest

from src.config import AppConfig


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    """Prevent real env vars and .env file from leaking into tests."""
    monkeypatch.chdir(tmp_path)
    for key in ("OPENAI_API_KEY", "COMPOSIO_API_KEY", "OPIK_API_KEY", "SPREADSHEET_ID", "COMPOSIO_USER_ID"):
        monkeypatch.delenv(key, raising=False)


class TestAppConfig:
    def test_creates_with_defaults(self):
        config = AppConfig()
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4o-mini"
        assert config.ocr_engine == "tesseract"
        assert config.tool_manager == "composio"
        assert config.prompt_store == "local"
        assert config.prompts_dir == "prompts"
        assert config.prompt_language == "en"
        assert config.prompt_fallback_language == "en"
        assert config.spreadsheet_id == ""
        assert config.opik_project == "po-workflow"

    def test_from_yaml(self, tmp_path):
        yaml_content = """\
llm_provider: openai
llm_model: gpt-4o
ocr_engine: tesseract
tool_manager: mock
prompt_store: local
prompts_dir: prompts
prompt_language: es
prompt_fallback_language: en
spreadsheet_id: sheet-abc
opik_project: my-project
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)

        config = AppConfig.from_yaml(yaml_file)
        assert config.llm_model == "gpt-4o"
        assert config.tool_manager == "mock"
        assert config.prompt_language == "es"
        assert config.spreadsheet_id == "sheet-abc"
        assert config.opik_project == "my-project"

    def test_from_yaml_with_real_config(self):
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        config = AppConfig.from_yaml(config_path)
        assert config.llm_provider == "openai"
        assert config.tool_manager == "composio"

    def test_from_yaml_with_eval_config(self):
        config_path = Path(__file__).parent.parent.parent / "config.eval.yaml"
        config = AppConfig.from_yaml(config_path)
        assert config.tool_manager == "mock"
        assert config.opik_project == "po-workflow-eval"

    def test_for_eval(self):
        config = AppConfig.for_eval()
        assert config.tool_manager == "mock"
        assert config.prompt_store == "local"
        assert config.prompts_dir == "prompts"

    def test_optional_fields_default_to_none(self):
        config = AppConfig()
        assert config.llm_base_url is None
        assert config.openai_api_key is None
        assert config.composio_api_key is None
        assert config.opik_api_key is None

    def test_reads_openai_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        config = AppConfig()
        assert config.openai_api_key == "sk-test-123"

    def test_reads_opik_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("OPIK_API_KEY", "op-test-456")
        config = AppConfig()
        assert config.opik_api_key == "op-test-456"

    def test_reads_composio_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("COMPOSIO_API_KEY", "comp-test-789")
        config = AppConfig()
        assert config.composio_api_key == "comp-test-789"

    def test_confidence_threshold_defaults_to_0_5(self):
        config = AppConfig()
        assert config.confidence_threshold == 0.5

    def test_confidence_threshold_from_yaml(self, tmp_path):
        yaml_content = "confidence_threshold: 0.7\n"
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)
        config = AppConfig.from_yaml(yaml_file)
        assert config.confidence_threshold == 0.7
