"""Unit tests for WorkflowBuilder and workflow graph compilation."""
from src.config import AppConfig
from src.builder import WorkflowBuilder
from src.services.tools.mock import MockToolManager
from src.services.prompt_store.local import LocalPromptStore


class TestWorkflowBuilder:
    def test_eval_config_creates_mock_tool_manager(self):
        config = AppConfig.for_eval()
        builder = WorkflowBuilder(config)
        assert isinstance(builder.tool_manager, MockToolManager)

    def test_eval_config_creates_local_prompt_store(self):
        config = AppConfig.for_eval()
        builder = WorkflowBuilder(config)
        assert isinstance(builder.prompt_store, LocalPromptStore)

    def test_build_returns_compiled_graph(self):
        config = AppConfig.for_eval()
        builder = WorkflowBuilder(config)
        graph = builder.build()
        assert graph is not None

    def test_exposes_tool_manager_for_eval_inspection(self):
        config = AppConfig.for_eval()
        builder = WorkflowBuilder(config)
        builder.build()
        # tool_manager should be accessible after build for graders
        mock = builder.tool_manager
        assert isinstance(mock, MockToolManager)
        assert len(mock.all_calls) == 0

    def test_graph_has_expected_nodes(self):
        config = AppConfig.for_eval()
        builder = WorkflowBuilder(config)
        graph = builder.build()
        # LangGraph compiled graph exposes nodes via .get_graph().nodes
        graph_info = graph.get_graph()
        node_names = [n.name for n in graph_info.nodes.values()]
        for expected in ["classify", "extract", "validate", "track", "notify", "report"]:
            assert expected in node_names, f"Node '{expected}' not found in graph"
