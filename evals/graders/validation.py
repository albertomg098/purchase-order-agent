from opik.evaluation.metrics import BaseMetric
from opik.evaluation.metrics.score_result import ScoreResult


class ValidationCorrectness(BaseMetric):
    """Checks that missing fields were correctly identified."""
    name = "validation_correctness"

    def score(self, missing_fields: list[str], expected_missing_fields: list[str], **kwargs) -> ScoreResult:
        expected_set = set(expected_missing_fields)
        actual_set = set(missing_fields)

        if not expected_set and not actual_set:
            return ScoreResult(value=1.0, name=self.name, reason="No missing fields expected or found")

        precision = len(expected_set & actual_set) / len(actual_set) if actual_set else (1.0 if not expected_set else 0.0)
        recall = len(expected_set & actual_set) / len(expected_set) if expected_set else 1.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return ScoreResult(
            value=f1,
            name=self.name,
            reason=f"P={precision:.2f} R={recall:.2f} F1={f1:.2f}. Expected: {expected_set}, Got: {actual_set}",
        )
