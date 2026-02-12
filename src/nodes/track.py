from src.nodes.base import BaseNode
from src.services.tools.base import ToolManager
from src.core.workflow_state import POWorkflowState


class TrackNode(BaseNode):
    name = "track"

    def __init__(self, tools: ToolManager, spreadsheet_id: str):
        self.tools = tools
        self.spreadsheet_id = spreadsheet_id

    def __call__(self, state: POWorkflowState) -> dict:
        raise NotImplementedError("TrackNode will be implemented in Phase 2")
