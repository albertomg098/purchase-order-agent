"""Unit tests for AppConfig."""
from pathlib import Path

from src.config import AppConfig


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
        config_path = Path(__file__).parent.parent / "config.yaml"
        config = AppConfig.from_yaml(config_path)
        assert config.llm_provider == "openai"
        assert config.tool_manager == "composio"

    def test_from_yaml_with_eval_config(self):
        config_path = Path(__file__).parent.parent / "config.eval.yaml"
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
        assert config.llm_api_key is None
        assert config.composio_api_key is None
