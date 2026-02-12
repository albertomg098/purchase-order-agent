from opik.evaluation.metrics import BaseMetric
from opik.evaluation.metrics.score_result import ScoreResult


class ClassificationAccuracy(BaseMetric):
    """Evaluates whether the email was correctly classified as PO or not."""
    name = "classification_accuracy"

    def score(self, is_valid_po: bool, expected_is_valid_po: bool, **kwargs) -> ScoreResult:
        correct = is_valid_po == expected_is_valid_po
        return ScoreResult(
            value=1.0 if correct else 0.0,
            name=self.name,
            reason=f"Expected {expected_is_valid_po}, got {is_valid_po}",
        )
