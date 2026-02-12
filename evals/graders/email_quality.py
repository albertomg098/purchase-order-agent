from opik.evaluation.metrics import BaseMetric
from opik.evaluation.metrics.score_result import ScoreResult


class EmailQuality(BaseMetric):
    """LLM-as-judge evaluation of the email response quality.

    Evaluates:
    - Professional tone
    - Mentions PO ID
    - Includes relevant order details
    - No hallucinated information
    - Appropriate next steps
    """
    name = "email_quality"

    def score(self, email_body: str | None, expected_extracted_data: dict | None, final_status: str, **kwargs) -> ScoreResult:
        if final_status == "skipped":
            # No email expected for skipped emails
            if email_body is None:
                return ScoreResult(value=1.0, name=self.name, reason="No email for skipped scenario")
            return ScoreResult(value=0.0, name=self.name, reason="Email sent for skipped scenario")

        if email_body is None:
            return ScoreResult(value=0.0, name=self.name, reason="No email sent")

        # Phase 1: heuristic checks only. LLM-as-judge in Phase 2.
        checks = []
        score = 0.0

        # Check 1: Email is not empty and has reasonable length
        if len(email_body) > 50:
            score += 0.25
            checks.append("sufficient_length")

        # Check 2: Mentions PO ID if available
        po_id = (expected_extracted_data or {}).get("order_id", "")
        if po_id and po_id in email_body:
            score += 0.25
            checks.append("mentions_po_id")

        # Check 3: Contains confirmation language
        confirmation_words = ["confirm", "received", "processing", "recibido", "procesando"]
        if any(w in email_body.lower() for w in confirmation_words):
            score += 0.25
            checks.append("confirmation_language")

        # Check 4: Contains customer name if available
        customer = (expected_extracted_data or {}).get("customer", "")
        if customer and customer.lower() in email_body.lower():
            score += 0.25
            checks.append("mentions_customer")

        return ScoreResult(
            value=score,
            name=self.name,
            reason=f"Checks passed: {checks}",
        )
