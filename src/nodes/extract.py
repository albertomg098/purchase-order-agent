from src.nodes.base import BaseNode
from src.services.ocr.base import OCRService
from src.services.llm.base import LLMService
from src.services.prompt_store.base import PromptStore
from src.core.workflow_state import POWorkflowState


class ExtractNode(BaseNode):
    name = "extract"

    def __init__(self, ocr: OCRService, llm: LLMService, prompt_store: PromptStore):
        self.ocr = ocr
        self.llm = llm
        self.prompt_store = prompt_store

    def __call__(self, state: POWorkflowState) -> dict:
        raise NotImplementedError("ExtractNode will be implemented in Phase 2")
