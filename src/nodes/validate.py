from src.nodes.base import BaseNode
from src.core.workflow_state import POWorkflowState


class ValidateNode(BaseNode):
    name = "validate"

    def __call__(self, state: POWorkflowState) -> dict:
        raise NotImplementedError("ValidateNode will be implemented in Phase 2")
