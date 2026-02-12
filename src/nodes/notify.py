from src.nodes.base import BaseNode
from src.services.llm.base import LLMService
from src.services.tools.base import ToolManager
from src.services.prompt_store.base import PromptStore
from src.core.workflow_state import POWorkflowState


class NotifyNode(BaseNode):
    name = "notify"

    def __init__(self, llm: LLMService, tools: ToolManager, prompt_store: PromptStore):
        self.llm = llm
        self.tools = tools
        self.prompt_store = prompt_store

    def __call__(self, state: POWorkflowState) -> dict:
        raise NotImplementedError("NotifyNode will be implemented in Phase 2")
