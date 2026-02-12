"""Unit tests for all 5 Opik BaseMetric graders."""
from evals.graders.classification import ClassificationAccuracy
from evals.graders.extraction import ExtractionAccuracy
from evals.graders.trajectory import TrajectoryCorrectness
from evals.graders.validation import ValidationCorrectness
from evals.graders.email_quality import EmailQuality


# --- ClassificationAccuracy ---


class TestClassificationAccuracy:
    def setup_method(self):
        self.grader = ClassificationAccuracy()

    def test_true_true_returns_1(self):
        result = self.grader.score(is_valid_po=True, expected_is_valid_po=True)
        assert result.value == 1.0

    def test_true_false_returns_0(self):
        result = self.grader.score(is_valid_po=True, expected_is_valid_po=False)
        assert result.value == 0.0

    def test_false_true_returns_0(self):
        result = self.grader.score(is_valid_po=False, expected_is_valid_po=True)
        assert result.value == 0.0

    def test_false_false_returns_1(self):
        result = self.grader.score(is_valid_po=False, expected_is_valid_po=False)
        assert result.value == 1.0

    def test_has_reason(self):
        result = self.grader.score(is_valid_po=True, expected_is_valid_po=False)
        assert result.reason is not None


# --- ExtractionAccuracy ---


class TestExtractionAccuracy:
    def setup_method(self):
        self.grader = ExtractionAccuracy()

    def test_all_match_returns_1(self):
        data = {
            "order_id": "PO-001",
            "customer": "Acme",
            "pickup_location": "Madrid",
            "delivery_location": "Barcelona",
            "delivery_datetime": "2025-01-18T08:00:00",
            "driver_name": "Juan",
            "driver_phone": "+34 600 123 456",
        }
        result = self.grader.score(extracted_data=data, expected_extracted_data=data)
        assert result.value == 1.0

    def test_half_match_returns_approximate_half(self):
        expected = {
            "order_id": "PO-001",
            "customer": "Acme",
            "pickup_location": "Madrid",
            "delivery_location": "Barcelona",
            "delivery_datetime": "2025-01-18T08:00:00",
            "driver_name": "Juan",
            "driver_phone": "+34 600 123 456",
        }
        actual = {
            "order_id": "PO-001",
            "customer": "Acme",
            "pickup_location": "Madrid",
            "delivery_location": "WRONG",
            "delivery_datetime": "WRONG",
            "driver_name": "WRONG",
            "driver_phone": "WRONG",
        }
        result = self.grader.score(extracted_data=actual, expected_extracted_data=expected)
        assert 0.4 <= result.value <= 0.5

    def test_none_none_returns_1(self):
        result = self.grader.score(extracted_data=None, expected_extracted_data=None)
        assert result.value == 1.0

    def test_none_expected_returns_0(self):
        expected = {
            "order_id": "PO-001",
            "customer": "Acme",
            "pickup_location": "Madrid",
            "delivery_location": "Barcelona",
            "delivery_datetime": "2025-01-18T08:00:00",
            "driver_name": "Juan",
            "driver_phone": "+34 600 123 456",
        }
        result = self.grader.score(extracted_data=None, expected_extracted_data=expected)
        assert result.value == 0.0

    def test_actual_none_expected_returns_0(self):
        result = self.grader.score(extracted_data={"order_id": "PO-001"}, expected_extracted_data=None)
        assert result.value == 0.0

    def test_normalization_whitespace(self):
        expected = {"order_id": "PO-001", "customer": "Acme Corp"}
        actual = {"order_id": "  PO-001  ", "customer": "  acme corp  "}
        result = self.grader.score(extracted_data=actual, expected_extracted_data=expected)
        # order_id and customer match after normalization; other fields are None in expected → skipped
        assert result.value == 1.0

    def test_normalization_case(self):
        expected = {"order_id": "PO-001", "customer": "ACME CORP"}
        actual = {"order_id": "po-001", "customer": "acme corp"}
        result = self.grader.score(extracted_data=actual, expected_extracted_data=expected)
        assert result.value == 1.0

    def test_missing_field_in_expected_skipped(self):
        expected = {
            "order_id": "PO-001",
            "customer": "Acme",
            "driver_phone": None,
        }
        actual = {
            "order_id": "PO-001",
            "customer": "Acme",
            "driver_phone": "whatever",
        }
        result = self.grader.score(extracted_data=actual, expected_extracted_data=expected)
        # order_id and customer match, driver_phone skipped (None in expected), rest skipped (not in expected)
        assert result.value == 1.0


# --- TrajectoryCorrectness ---


class TestTrajectoryCorrectness:
    def setup_method(self):
        self.grader = TrajectoryCorrectness()

    def test_exact_match_returns_1(self):
        traj = ["classify", "extract", "validate", "track", "notify", "report"]
        result = self.grader.score(trajectory=traj, expected_trajectory=traj)
        assert result.value == 1.0

    def test_different_order_returns_0(self):
        expected = ["classify", "extract", "validate"]
        actual = ["extract", "classify", "validate"]
        result = self.grader.score(trajectory=actual, expected_trajectory=expected)
        assert result.value == 0.0

    def test_subset_returns_0(self):
        expected = ["classify", "extract", "validate"]
        actual = ["classify", "extract"]
        result = self.grader.score(trajectory=actual, expected_trajectory=expected)
        assert result.value == 0.0

    def test_superset_returns_0(self):
        expected = ["classify"]
        actual = ["classify", "extract"]
        result = self.grader.score(trajectory=actual, expected_trajectory=expected)
        assert result.value == 0.0

    def test_both_empty_returns_1(self):
        result = self.grader.score(trajectory=[], expected_trajectory=[])
        assert result.value == 1.0


# --- ValidationCorrectness ---


class TestValidationCorrectness:
    def setup_method(self):
        self.grader = ValidationCorrectness()

    def test_empty_empty_returns_1(self):
        result = self.grader.score(missing_fields=[], expected_missing_fields=[])
        assert result.value == 1.0

    def test_perfect_match_returns_1(self):
        fields = ["driver_phone", "driver_name"]
        result = self.grader.score(missing_fields=fields, expected_missing_fields=fields)
        assert result.value == 1.0

    def test_partial_overlap_returns_f1(self):
        expected = ["driver_phone", "driver_name"]
        actual = ["driver_phone", "customer"]
        result = self.grader.score(missing_fields=actual, expected_missing_fields=expected)
        # precision = 1/2, recall = 1/2, F1 = 0.5
        assert result.value == 0.5

    def test_no_overlap_returns_0(self):
        expected = ["driver_phone"]
        actual = ["customer"]
        result = self.grader.score(missing_fields=actual, expected_missing_fields=expected)
        assert result.value == 0.0

    def test_actual_empty_expected_nonempty_returns_0(self):
        result = self.grader.score(missing_fields=[], expected_missing_fields=["driver_phone"])
        assert result.value == 0.0

    def test_actual_nonempty_expected_empty_returns_0(self):
        result = self.grader.score(missing_fields=["driver_phone"], expected_missing_fields=[])
        assert result.value == 0.0


# --- EmailQuality ---


class TestEmailQuality:
    def setup_method(self):
        self.grader = EmailQuality()

    def test_full_quality_email_returns_1(self):
        email = (
            "Dear Acme Logistics Ltd.,\n\n"
            "We have received your purchase order PO-2025-001 and confirm "
            "that it is now being processed. We will update you once the "
            "delivery has been scheduled.\n\n"
            "Best regards,\nTraza Logistics"
        )
        expected_data = {"order_id": "PO-2025-001", "customer": "Acme Logistics Ltd."}
        result = self.grader.score(
            email_body=email,
            expected_extracted_data=expected_data,
            final_status="completed",
        )
        assert result.value == 1.0

    def test_empty_email_returns_0(self):
        result = self.grader.score(
            email_body="",
            expected_extracted_data={"order_id": "PO-001"},
            final_status="completed",
        )
        assert result.value == 0.0

    def test_none_email_returns_0(self):
        result = self.grader.score(
            email_body=None,
            expected_extracted_data={"order_id": "PO-001"},
            final_status="completed",
        )
        assert result.value == 0.0

    def test_skipped_no_email_returns_1(self):
        result = self.grader.score(
            email_body=None,
            expected_extracted_data=None,
            final_status="skipped",
        )
        assert result.value == 1.0

    def test_skipped_with_email_returns_0(self):
        result = self.grader.score(
            email_body="Some email that should not have been sent",
            expected_extracted_data=None,
            final_status="skipped",
        )
        assert result.value == 0.0

    def test_partial_checks(self):
        # Long enough but missing PO ID, customer, and confirmation language
        email = "x" * 60
        result = self.grader.score(
            email_body=email,
            expected_extracted_data={"order_id": "PO-001", "customer": "Acme"},
            final_status="completed",
        )
        assert result.value == 0.25  # only sufficient_length passes
