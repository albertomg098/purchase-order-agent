import opik

from src.nodes.base import BaseNode
from src.core.workflow_state import POWorkflowState


class ReportNode(BaseNode):
    name = "report"

    @opik.track(name="report_node")
    def __call__(self, state: POWorkflowState) -> dict:
        if state.get("error_message"):
            final_status = "error"
        elif not state.get("is_valid_po"):
            final_status = "skipped"
        elif state.get("missing_fields"):
            final_status = "missing_info"
        else:
            final_status = "completed"

        return {
            "final_status": final_status,
            "trajectory": state.get("trajectory", []) + ["report"],
        }
