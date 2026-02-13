"""Unit tests for TrackNode."""
from src.nodes.track import TrackNode
from src.services.tools.mock import MockToolManager


FULL_DATA = {
    "order_id": "PO-2025-001",
    "customer": "Acme Corp",
    "pickup_location": "Warehouse A",
    "delivery_location": "Retail Hub B",
    "delivery_datetime": "2025-01-18T08:00:00",
    "driver_name": "Juan Pérez",
    "driver_phone": "+34 600 123 456",
}


def _make_node():
    tools = MockToolManager()
    return TrackNode(tools=tools, spreadsheet_id="sheet-123"), tools


class TestTrackNodeHappyPath:
    def test_appends_correct_row(self):
        node, tools = _make_node()
        state = {
            "is_valid_po": True,
            "po_id": "PO-2025-001",
            "extracted_data": FULL_DATA,
            "missing_fields": [],
        }

        result = node(state)

        assert result["sheet_row_added"] is True
        rows = tools.sheet_rows_added
        assert len(rows) == 1
        row_values = rows[0]["values"]
        assert "PO-2025-001" in row_values
        assert "Acme Corp" in row_values
        assert "complete" in row_values

    def test_row_status_pending_when_missing_fields(self):
        node, tools = _make_node()
        state = {
            "is_valid_po": True,
            "po_id": "PO-2025-001",
            "extracted_data": FULL_DATA,
            "missing_fields": ["driver_phone"],
        }

        node(state)

        rows = tools.sheet_rows_added
        row_values = rows[0]["values"]
        assert "pending_info" in row_values

    def test_uses_correct_spreadsheet_id(self):
        node, tools = _make_node()
        state = {
            "is_valid_po": True,
            "po_id": "PO-2025-001",
            "extracted_data": FULL_DATA,
            "missing_fields": [],
        }

        node(state)

        rows = tools.sheet_rows_added
        assert rows[0]["spreadsheet_id"] == "sheet-123"

    def test_trajectory_updated(self):
        node, _ = _make_node()
        state = {
            "is_valid_po": True,
            "po_id": "PO-2025-001",
            "extracted_data": FULL_DATA,
            "missing_fields": [],
            "trajectory": ["classify", "extract", "validate"],
        }

        result = node(state)

        assert result["trajectory"] == ["classify", "extract", "validate", "track"]


class TestTrackNodeSkip:
    def test_skips_when_not_valid_po(self):
        node, tools = _make_node()
        state = {"is_valid_po": False, "trajectory": ["classify"]}

        result = node(state)

        assert "sheet_row_added" not in result
        assert tools.sheet_rows_added == []
        assert result["trajectory"] == ["classify", "track"]


class TestTrackNodeErrorHandling:
    def test_error_guard_passes_through(self):
        node, tools = _make_node()
        state = {
            "final_status": "error",
            "error_message": "Previous node failed",
            "trajectory": ["classify", "extract", "validate"],
        }

        result = node(state)

        assert result["trajectory"] == ["classify", "extract", "validate", "track"]
        assert "sheet_row_added" not in result
        assert tools.sheet_rows_added == []
