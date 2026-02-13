"""Unit tests for WorkflowBuilder and workflow graph compilation."""
from unittest.mock import patch

import pytest

from src.config import AppConfig
from src.builder import WorkflowBuilder
from src.services.llm.openai import OpenAILLM
from src.services.ocr.tesseract import TesseractOCR
from src.services.tools.mock import MockToolManager
from src.services.tools.composio import ComposioToolManager
from src.services.prompt_store.local import LocalPromptStore

MOCK_OPENAI = "src.services.llm.openai.OpenAI"
MOCK_COMPOSIO = "src.services.tools.composio.Composio"


class TestWorkflowBuilder:
    def test_eval_config_creates_mock_tool_manager(self):
        with patch(MOCK_OPENAI):
            config = AppConfig.for_eval()
            builder = WorkflowBuilder(config)
        assert isinstance(builder.tool_manager, MockToolManager)

    def test_eval_config_creates_local_prompt_store(self):
        with patch(MOCK_OPENAI):
            config = AppConfig.for_eval()
            builder = WorkflowBuilder(config)
        assert isinstance(builder.prompt_store, LocalPromptStore)

    def test_build_returns_compiled_graph(self):
        with patch(MOCK_OPENAI):
            config = AppConfig.for_eval()
            builder = WorkflowBuilder(config)
            graph = builder.build()
        assert graph is not None

    def test_exposes_tool_manager_for_eval_inspection(self):
        with patch(MOCK_OPENAI):
            config = AppConfig.for_eval()
            builder = WorkflowBuilder(config)
            builder.build()
            mock = builder.tool_manager
        assert isinstance(mock, MockToolManager)
        assert len(mock.all_calls) == 0

    def test_graph_has_expected_nodes(self):
        with patch(MOCK_OPENAI):
            config = AppConfig.for_eval()
            builder = WorkflowBuilder(config)
            graph = builder.build()
        graph_info = graph.get_graph()
        node_names = [n.name for n in graph_info.nodes.values()]
        for expected in ["classify", "extract", "validate", "track", "notify", "report"]:
            assert expected in node_names, f"Node '{expected}' not found in graph"


class TestBuilderServiceCreation:
    def test_openai_provider_creates_openai_llm(self):
        with patch(MOCK_OPENAI):
            config = AppConfig.for_eval()
            builder = WorkflowBuilder(config)
        assert isinstance(builder._llm, OpenAILLM)

    def test_openai_llm_receives_config_params(self):
        config = AppConfig(
            tool_manager="mock",
            openai_api_key="sk-test-key",
            llm_model="gpt-4o",
            llm_base_url="https://custom.api",
        )
        with patch(MOCK_OPENAI):
            builder = WorkflowBuilder(config)
        assert builder._llm._model == "gpt-4o"

    def test_tesseract_engine_creates_tesseract_ocr(self):
        with patch(MOCK_OPENAI):
            config = AppConfig.for_eval()
            builder = WorkflowBuilder(config)
        assert isinstance(builder._ocr, TesseractOCR)

    def test_mock_tool_manager_created(self):
        with patch(MOCK_OPENAI):
            config = AppConfig(tool_manager="mock")
            builder = WorkflowBuilder(config)
        assert isinstance(builder._tool_manager, MockToolManager)

    def test_unknown_llm_provider_raises(self):
        config = AppConfig(tool_manager="mock", llm_provider="unknown")
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            WorkflowBuilder(config)

    def test_unknown_ocr_engine_raises(self):
        with patch(MOCK_OPENAI):
            config = AppConfig(tool_manager="mock", ocr_engine="unknown")
            with pytest.raises(ValueError, match="Unknown OCR engine"):
                WorkflowBuilder(config)

    def test_unknown_tool_manager_raises(self):
        with patch(MOCK_OPENAI):
            config = AppConfig(tool_manager="unknown")
            with pytest.raises(ValueError, match="Unknown tool manager"):
                WorkflowBuilder(config)

    def test_validate_node_gets_confidence_threshold(self):
        with patch(MOCK_OPENAI):
            config = AppConfig(tool_manager="mock", confidence_threshold=0.7)
            builder = WorkflowBuilder(config)
            graph = builder.build()
        assert graph is not None

    def test_composio_tool_manager_created(self):
        with patch(MOCK_OPENAI), patch(MOCK_COMPOSIO):
            config = AppConfig(
                tool_manager="composio",
                composio_api_key="test-key",
                composio_user_id="entity-123",
                composio_toolkit_versions={"gmail": "20251027_00"},
            )
            builder = WorkflowBuilder(config)
        assert isinstance(builder._tool_manager, ComposioToolManager)

    def test_composio_tool_manager_receives_config_params(self):
        with patch(MOCK_OPENAI), patch(MOCK_COMPOSIO) as mock_cls:
            config = AppConfig(
                tool_manager="composio",
                composio_api_key="test-key",
                composio_user_id="entity-123",
                composio_toolkit_versions={"gmail": "20251027_00", "googlesheets": "20251027_00"},
            )
            builder = WorkflowBuilder(config)
        mock_cls.assert_called_once_with(
            api_key="test-key",
            toolkit_versions={"gmail": "20251027_00", "googlesheets": "20251027_00"},
        )
        assert builder._tool_manager._user_id == "entity-123"
