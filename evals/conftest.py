"""Pytest fixtures for evaluation runs."""
import json
from pathlib import Path
import pytest

from src.config import AppConfig
from src.builder import WorkflowBuilder
from src.services.tools.mock import MockToolManager

SCENARIOS_DIR = Path("evals/scenarios")
FIXTURES_DIR = Path("evals/fixtures")


@pytest.fixture
def eval_config() -> AppConfig:
    """AppConfig pre-configured for evaluation."""
    return AppConfig.for_eval()


@pytest.fixture
def mock_tools() -> MockToolManager:
    """Fresh MockToolManager instance, reset between tests."""
    mock = MockToolManager()
    yield mock
    mock.reset()


@pytest.fixture
def eval_workflow(eval_config):
    """Compiled workflow with mock tools for evaluation."""
    builder = WorkflowBuilder(eval_config)
    return builder.build(), builder.tool_manager


def load_scenarios(category: str | None = None) -> list[dict]:
    """Load scenarios from JSON files, optionally filtered by category."""
    scenarios = []
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        for s in data["scenarios"]:
            if category is None or s["category"] == category:
                scenarios.append(s)
    return scenarios


def load_pdf_fixture(fixture_path: str) -> bytes | None:
    """Load a PDF fixture by relative path."""
    if not fixture_path:
        return None
    path = FIXTURES_DIR / fixture_path
    return path.read_bytes() if path.exists() else None
