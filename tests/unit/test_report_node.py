"""Unit tests for ReportNode (pure logic, no service dependencies)."""
from src.nodes.report import ReportNode


class TestReportNodeStatus:
    def test_completed_status(self):
        node = ReportNode()
        state = {
            "is_valid_po": True,
            "missing_fields": [],
        }

        result = node(state)

        assert result["final_status"] == "completed"

    def test_missing_info_status(self):
        node = ReportNode()
        state = {
            "is_valid_po": True,
            "missing_fields": ["driver_phone"],
        }

        result = node(state)

        assert result["final_status"] == "missing_info"

    def test_skipped_status(self):
        node = ReportNode()
        state = {
            "is_valid_po": False,
        }

        result = node(state)

        assert result["final_status"] == "skipped"

    def test_error_status(self):
        node = ReportNode()
        state = {
            "is_valid_po": True,
            "missing_fields": [],
            "error_message": "ClassifyNode failed: timeout",
        }

        result = node(state)

        assert result["final_status"] == "error"

    def test_error_takes_precedence(self):
        node = ReportNode()
        state = {
            "is_valid_po": True,
            "missing_fields": ["driver_phone"],
            "error_message": "Something broke",
        }

        result = node(state)

        assert result["final_status"] == "error"


class TestReportNodeTrajectory:
    def test_trajectory_updated(self):
        node = ReportNode()
        state = {
            "is_valid_po": True,
            "missing_fields": [],
            "trajectory": ["classify", "extract", "validate", "track", "notify"],
        }

        result = node(state)

        assert result["trajectory"] == ["classify", "extract", "validate", "track", "notify", "report"]

    def test_trajectory_short_path(self):
        node = ReportNode()
        state = {
            "is_valid_po": False,
            "trajectory": ["classify"],
        }

        result = node(state)

        assert result["trajectory"] == ["classify", "report"]
