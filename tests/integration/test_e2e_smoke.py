"""E2E smoke test: scenarios → graders contract.

Verifies that a perfect result state scores 1.0 on all graders,
and an imperfect result state scores < 1.0. Does NOT invoke the
workflow (nodes are stubs) — tests the eval infrastructure only.
"""
import json
from pathlib import Path

from evals.graders.classification import ClassificationAccuracy
from evals.graders.extraction import ExtractionAccuracy
from evals.graders.trajectory import TrajectoryCorrectness
from evals.graders.validation import ValidationCorrectness
from evals.graders.email_quality import EmailQuality

SCENARIOS_DIR = Path("evals/scenarios")
FIXTURES_DIR = Path("evals/fixtures")


def _load_happy_path_scenario() -> dict:
    with open(SCENARIOS_DIR / "happy_path.json") as f:
        data = json.load(f)
    return data["scenarios"][0]


def _build_perfect_result(scenario: dict) -> dict:
    """Build a result state that perfectly matches expected values."""
    expected = scenario["expected"]
    po_id = expected["po_id"]
    extracted = expected["extracted_data"]

    # Simulate the confirmation email a real workflow would produce
    email_body = (
        f"Dear {extracted['customer']},\n\n"
        f"We have received your purchase order {po_id} and confirm "
        f"that it is now being processed.\n\n"
        f"Best regards,\nTraza Logistics"
    )

    return {
        "is_valid_po": expected["is_valid_po"],
        "extracted_data": extracted,
        "trajectory": expected["expected_trajectory"],
        "missing_fields": expected["missing_fields"],
        "final_status": expected["final_status"],
        "email_body": email_body,
        # Expected values for graders
        "expected_is_valid_po": expected["is_valid_po"],
        "expected_extracted_data": extracted,
        "expected_trajectory": expected["expected_trajectory"],
        "expected_missing_fields": expected["missing_fields"],
    }


class TestE2ESmokePerfect:
    """Perfect result state → all graders return 1.0."""

    def setup_method(self):
        self.scenario = _load_happy_path_scenario()
        self.result = _build_perfect_result(self.scenario)

    def test_pdf_fixture_loads(self):
        fixture_path = self.scenario["input"]["pdf_fixture"]
        pdf_path = FIXTURES_DIR / fixture_path
        assert pdf_path.exists(), f"PDF fixture not found: {pdf_path}"
        pdf_bytes = pdf_path.read_bytes()
        assert len(pdf_bytes) > 0

    def test_classification_accuracy_perfect(self):
        grader = ClassificationAccuracy()
        score = grader.score(
            is_valid_po=self.result["is_valid_po"],
            expected_is_valid_po=self.result["expected_is_valid_po"],
        )
        assert score.value == 1.0

    def test_extraction_accuracy_perfect(self):
        grader = ExtractionAccuracy()
        score = grader.score(
            extracted_data=self.result["extracted_data"],
            expected_extracted_data=self.result["expected_extracted_data"],
        )
        assert score.value == 1.0

    def test_trajectory_correctness_perfect(self):
        grader = TrajectoryCorrectness()
        score = grader.score(
            trajectory=self.result["trajectory"],
            expected_trajectory=self.result["expected_trajectory"],
        )
        assert score.value == 1.0

    def test_validation_correctness_perfect(self):
        grader = ValidationCorrectness()
        score = grader.score(
            missing_fields=self.result["missing_fields"],
            expected_missing_fields=self.result["expected_missing_fields"],
        )
        assert score.value == 1.0

    def test_email_quality_perfect(self):
        grader = EmailQuality()
        score = grader.score(
            email_body=self.result["email_body"],
            expected_extracted_data=self.result["expected_extracted_data"],
            final_status=self.result["final_status"],
        )
        assert score.value == 1.0


class TestE2ESmokeImperfect:
    """Imperfect result state → graders return < 1.0."""

    def setup_method(self):
        self.scenario = _load_happy_path_scenario()
        self.result = _build_perfect_result(self.scenario)

    def test_wrong_classification(self):
        grader = ClassificationAccuracy()
        score = grader.score(
            is_valid_po=False,  # wrong
            expected_is_valid_po=self.result["expected_is_valid_po"],
        )
        assert score.value < 1.0

    def test_wrong_extraction_field(self):
        grader = ExtractionAccuracy()
        bad_data = dict(self.result["extracted_data"])
        bad_data["customer"] = "WRONG COMPANY"
        score = grader.score(
            extracted_data=bad_data,
            expected_extracted_data=self.result["expected_extracted_data"],
        )
        assert score.value < 1.0

    def test_wrong_trajectory(self):
        grader = TrajectoryCorrectness()
        score = grader.score(
            trajectory=["classify", "extract"],  # incomplete
            expected_trajectory=self.result["expected_trajectory"],
        )
        assert score.value < 1.0

    def test_spurious_missing_fields(self):
        grader = ValidationCorrectness()
        score = grader.score(
            missing_fields=["driver_phone"],  # falsely flagged
            expected_missing_fields=self.result["expected_missing_fields"],  # empty
        )
        assert score.value < 1.0

    def test_no_email_sent(self):
        grader = EmailQuality()
        score = grader.score(
            email_body=None,  # no email
            expected_extracted_data=self.result["expected_extracted_data"],
            final_status=self.result["final_status"],
        )
        assert score.value < 1.0

    def test_email_missing_po_id(self):
        grader = EmailQuality()
        # Long enough email but without PO ID or customer name
        score = grader.score(
            email_body="Thank you for your order. We will process it shortly. " * 3,
            expected_extracted_data=self.result["expected_extracted_data"],
            final_status=self.result["final_status"],
        )
        assert score.value < 1.0
