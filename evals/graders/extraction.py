from opik.evaluation.metrics import BaseMetric
from opik.evaluation.metrics.score_result import ScoreResult


EXTRACTION_FIELDS = [
    "order_id", "customer", "pickup_location", "delivery_location",
    "delivery_datetime", "driver_name", "driver_phone",
]


class ExtractionAccuracy(BaseMetric):
    """Field-level extraction accuracy. Compares each field independently."""
    name = "extraction_accuracy"

    def score(self, extracted_data: dict | None, expected_extracted_data: dict | None, **kwargs) -> ScoreResult:
        if expected_extracted_data is None:
            # Not a PO scenario — extraction not expected
            return ScoreResult(value=1.0 if extracted_data is None else 0.0, name=self.name)

        if extracted_data is None:
            return ScoreResult(value=0.0, name=self.name, reason="No data extracted")

        correct = 0
        total = len(EXTRACTION_FIELDS)
        mismatches = []

        for field in EXTRACTION_FIELDS:
            expected = expected_extracted_data.get(field)
            actual = extracted_data.get(field)

            if expected is None:
                # Field intentionally missing in ground truth — skip
                total -= 1
                continue

            if self._normalize(actual) == self._normalize(expected):
                correct += 1
            else:
                mismatches.append(f"{field}: expected '{expected}', got '{actual}'")

        score = correct / total if total > 0 else 1.0
        return ScoreResult(
            value=score,
            name=self.name,
            reason=f"{correct}/{total} fields correct. Mismatches: {mismatches}" if mismatches else f"{correct}/{total} fields correct",
        )

    @staticmethod
    def _normalize(value: str | None) -> str | None:
        """Normalize for comparison: lowercase, strip whitespace."""
        if value is None:
            return None
        return str(value).strip().lower()
