from src.nodes.base import BaseNode
from src.core.workflow_state import POWorkflowState


class ReportNode(BaseNode):
    name = "report"

    def __call__(self, state: POWorkflowState) -> dict:
        raise NotImplementedError("ReportNode will be implemented in Phase 2")
