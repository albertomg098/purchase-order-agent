from src.nodes.base import BaseNode
from src.services.tools.base import ToolManager
from src.core.workflow_state import POWorkflowState


class TrackNode(BaseNode):
    name = "track"

    def __init__(self, tools: ToolManager, spreadsheet_id: str):
        self.tools = tools
        self.spreadsheet_id = spreadsheet_id

    def __call__(self, state: POWorkflowState) -> dict:
        if state.get("final_status") == "error":
            return {"trajectory": state.get("trajectory", []) + ["track"]}

        if not state.get("is_valid_po"):
            return {"trajectory": state.get("trajectory", []) + ["track"]}

        try:
            extracted_data = state.get("extracted_data") or {}
            missing_fields = state.get("missing_fields", [])
            row_status = "complete" if not missing_fields else "pending_info"

            values = [
                state.get("po_id", ""),
                extracted_data.get("customer", ""),
                extracted_data.get("pickup_location", ""),
                extracted_data.get("delivery_location", ""),
                extracted_data.get("delivery_datetime", ""),
                extracted_data.get("driver_name", ""),
                extracted_data.get("driver_phone", ""),
                row_status,
            ]

            self.tools.append_sheet_row(self.spreadsheet_id, values)

            return {
                "sheet_row_added": True,
                "trajectory": state.get("trajectory", []) + ["track"],
            }
        except Exception as e:
            return {
                "final_status": "error",
                "error_message": f"TrackNode failed: {e}",
                "trajectory": state.get("trajectory", []) + ["track"],
            }
