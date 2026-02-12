from opik.evaluation.metrics import BaseMetric
from opik.evaluation.metrics.score_result import ScoreResult


class TrajectoryCorrectness(BaseMetric):
    """Checks that the workflow visited the expected sequence of nodes."""
    name = "trajectory_correctness"

    def score(self, trajectory: list[str], expected_trajectory: list[str], **kwargs) -> ScoreResult:
        correct = trajectory == expected_trajectory
        return ScoreResult(
            value=1.0 if correct else 0.0,
            name=self.name,
            reason=f"Expected {expected_trajectory}, got {trajectory}",
        )
