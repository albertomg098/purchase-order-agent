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
        raise NotImplementedError("ClassifyNode will be implemented in Phase 2")
