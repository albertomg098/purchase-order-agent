import opik

from src.nodes.base import BaseNode
from src.core.workflow_state import POWorkflowState

REQUIRED_FIELDS = [
    "order_id", "customer", "pickup_location", "delivery_location",
    "delivery_datetime", "driver_name", "driver_phone",
]


class ValidateNode(BaseNode):
    name = "validate"

    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold

    @opik.track(name="validate_node")
    def __call__(self, state: POWorkflowState) -> dict:
        if state.get("final_status") == "error":
            return {"trajectory": state.get("trajectory", []) + ["validate"]}

        extracted_data = state.get("extracted_data") or {}
        field_confidences = state.get("field_confidences") or {}

        missing_fields = []
        validation_errors = []

        for field in REQUIRED_FIELDS:
            value = extracted_data.get(field)
            confidence = field_confidences.get(field, 0.0)

            if value is None or value == "":
                missing_fields.append(field)
                validation_errors.append(f"Field '{field}' is missing or empty")
            elif confidence < self.confidence_threshold:
                missing_fields.append(field)
                validation_errors.append(f"Field '{field}' has low confidence ({confidence})")

        return {
            "missing_fields": missing_fields,
            "validation_errors": validation_errors,
            "trajectory": state.get("trajectory", []) + ["validate"],
        }
