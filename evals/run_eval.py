"""
Main evaluation runner. Uses opik.evaluate() to run all scenarios
against the workflow and compute metrics.

Usage:
    python -m evals.run_eval
    python -m evals.run_eval --category happy_path
"""
import json
import argparse
from pathlib import Path

import opik
from opik import Opik
from opik.evaluation import evaluate

from evals.graders.classification import ClassificationAccuracy
from evals.graders.extraction import ExtractionAccuracy
from evals.graders.trajectory import TrajectoryCorrectness
from evals.graders.validation import ValidationCorrectness
from evals.graders.email_quality import EmailQuality

from src.config import AppConfig
from src.builder import WorkflowBuilder


SCENARIOS_DIR = Path("evals/scenarios")
FIXTURES_DIR = Path("evals/fixtures")


def load_scenarios(category: str | None = None) -> list[dict]:
    """Load scenarios from JSON files, optionally filtered by category."""
    scenarios = []
    for path in SCENARIOS_DIR.glob("*.json"):
        with open(path) as f:
            data = json.load(f)
        for s in data["scenarios"]:
            if category is None or s["category"] == category:
                scenarios.append(s)
    return scenarios


def build_eval_task(workflow, mock_tools):
    """Build the task function that opik.evaluate() will call for each scenario."""

    @opik.track(name="po_workflow")
    def eval_task(scenario: dict) -> dict:
        mock_tools.reset()

        # Load PDF fixture if specified
        pdf_bytes = None
        pdf_fixture = scenario["input"].get("pdf_fixture")
        if pdf_fixture:
            pdf_path = FIXTURES_DIR / pdf_fixture
            if pdf_path.exists():
                pdf_bytes = pdf_path.read_bytes()

        # Build workflow input state
        input_state = {
            "email_subject": scenario["input"]["email_subject"],
            "email_body": scenario["input"]["email_body"],
            "email_sender": scenario["input"]["email_sender"],
            "email_message_id": scenario["input"].get("email_message_id", "test"),
            "has_attachment": scenario["input"]["has_attachment"],
            "pdf_bytes": pdf_bytes,
            "actions_log": [],
            "trajectory": [],
        }

        # Run workflow
        result = workflow.invoke(input_state)

        # Extract email body from mock for email quality grading
        emails = mock_tools.emails_sent
        email_body = emails[0]["body"] if emails else None

        # Return dict matching what graders expect
        return {
            "is_valid_po": result.get("is_valid_po", False),
            "extracted_data": result.get("extracted_data"),
            "trajectory": result.get("trajectory", []),
            "missing_fields": result.get("missing_fields", []),
            "final_status": result.get("final_status", "error"),
            "email_body": email_body,
            # Pass through expected values for graders
            "expected_is_valid_po": scenario["expected"]["is_valid_po"],
            "expected_extracted_data": scenario["expected"].get("extracted_data"),
            "expected_trajectory": scenario["expected"]["expected_trajectory"],
            "expected_missing_fields": scenario["expected"].get("missing_fields", []),
        }

    return eval_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, default=None)
    parser.add_argument("--experiment-name", type=str, default=None)
    args = parser.parse_args()

    # Build workflow with mock tools
    config = AppConfig.for_eval()
    builder = WorkflowBuilder(config)
    workflow = builder.build()
    mock_tools = builder.tool_manager  # Access the mock for inspection

    # Load scenarios into Opik dataset
    scenarios = load_scenarios(args.category)
    client = Opik()
    dataset_name = f"po-scenarios-{args.category}" if args.category else "po-scenarios-all"
    dataset = client.get_or_create_dataset(dataset_name)

    # Opik requires 'id' to be a UUID; rename our string ids to 'scenario_id'
    dataset_items = []
    for s in scenarios:
        item = {**s}
        item["scenario_id"] = item.pop("id", None)
        dataset_items.append(item)
    dataset.insert(dataset_items)

    # Run evaluation (task_threads=1 because tasks share mutable mock_tools state)
    evaluate(
        dataset=dataset,
        task=build_eval_task(workflow, mock_tools),
        scoring_metrics=[
            ClassificationAccuracy(),
            ExtractionAccuracy(),
            TrajectoryCorrectness(),
            ValidationCorrectness(),
            EmailQuality(),
        ],
        experiment_name=args.experiment_name or "po-workflow-eval",
        experiment_config={
            "llm_model": config.llm_model,
            "category": args.category or "all",
        },
        task_threads=1,
    )


if __name__ == "__main__":
    main()
