"""Unit tests for ValidateNode (pure logic, no service mocks needed)."""
from src.nodes.validate import ValidateNode


REQUIRED_FIELDS = [
    "order_id", "customer", "pickup_location", "delivery_location",
    "delivery_datetime", "driver_name", "driver_phone",
]

FULL_DATA = {
    "order_id": "PO-2025-001",
    "customer": "Acme Corp",
    "pickup_location": "Warehouse A",
    "delivery_location": "Retail Hub B",
    "delivery_datetime": "2025-01-18T08:00:00",
    "driver_name": "Juan Pérez",
    "driver_phone": "+34 600 123 456",
}

FULL_CONFIDENCES = {field: 0.9 for field in REQUIRED_FIELDS}


class TestValidateNodeConstructor:
    def test_default_threshold(self):
        node = ValidateNode()
        assert node.confidence_threshold == 0.5

    def test_custom_threshold(self):
        node = ValidateNode(confidence_threshold=0.7)
        assert node.confidence_threshold == 0.7


class TestValidateNodeHappyPath:
    def test_no_missing_fields(self):
        node = ValidateNode()
        state = {
            "extracted_data": FULL_DATA,
            "field_confidences": FULL_CONFIDENCES,
        }

        result = node(state)

        assert result["missing_fields"] == []
        assert result["validation_errors"] == []

    def test_trajectory_updated(self):
        node = ValidateNode()
        state = {
            "extracted_data": FULL_DATA,
            "field_confidences": FULL_CONFIDENCES,
            "trajectory": ["classify", "extract"],
        }

        result = node(state)

        assert result["trajectory"] == ["classify", "extract", "validate"]


class TestValidateNodeMissingFields:
    def test_none_field_detected(self):
        node = ValidateNode()
        data = {**FULL_DATA, "driver_phone": None}
        confidences = {**FULL_CONFIDENCES, "driver_phone": 0.0}
        state = {"extracted_data": data, "field_confidences": confidences}

        result = node(state)

        assert "driver_phone" in result["missing_fields"]

    def test_empty_string_field_detected(self):
        node = ValidateNode()
        data = {**FULL_DATA, "customer": ""}
        confidences = {**FULL_CONFIDENCES, "customer": 0.9}
        state = {"extracted_data": data, "field_confidences": confidences}

        result = node(state)

        assert "customer" in result["missing_fields"]

    def test_low_confidence_field_detected(self):
        node = ValidateNode(confidence_threshold=0.5)
        confidences = {**FULL_CONFIDENCES, "driver_name": 0.3}
        state = {"extracted_data": FULL_DATA, "field_confidences": confidences}

        result = node(state)

        assert "driver_name" in result["missing_fields"]

    def test_high_confidence_field_not_flagged(self):
        node = ValidateNode(confidence_threshold=0.5)
        confidences = {**FULL_CONFIDENCES, "driver_name": 0.5}
        state = {"extracted_data": FULL_DATA, "field_confidences": confidences}

        result = node(state)

        assert "driver_name" not in result["missing_fields"]

    def test_multiple_missing_fields(self):
        node = ValidateNode()
        data = {**FULL_DATA, "driver_phone": None, "customer": ""}
        confidences = {**FULL_CONFIDENCES, "driver_phone": 0.0, "customer": 0.9}
        state = {"extracted_data": data, "field_confidences": confidences}

        result = node(state)

        assert "driver_phone" in result["missing_fields"]
        assert "customer" in result["missing_fields"]

    def test_missing_field_from_extracted_data(self):
        node = ValidateNode()
        data = {k: v for k, v in FULL_DATA.items() if k != "driver_phone"}
        confidences = {k: v for k, v in FULL_CONFIDENCES.items() if k != "driver_phone"}
        state = {"extracted_data": data, "field_confidences": confidences}

        result = node(state)

        assert "driver_phone" in result["missing_fields"]


class TestValidateNodeErrorHandling:
    def test_error_guard_passes_through(self):
        node = ValidateNode()
        state = {
            "final_status": "error",
            "error_message": "Previous node failed",
            "trajectory": ["classify", "extract"],
        }

        result = node(state)

        assert result["trajectory"] == ["classify", "extract", "validate"]
        assert "missing_fields" not in result
