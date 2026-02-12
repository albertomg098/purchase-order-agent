"""Sync local JSON scenarios to Opik dataset."""
import json
from pathlib import Path
from opik import Opik

SCENARIOS_DIR = Path("evals/scenarios")


def sync():
    client = Opik()
    all_scenarios = []

    for path in SCENARIOS_DIR.glob("*.json"):
        with open(path) as f:
            data = json.load(f)
        all_scenarios.extend(data["scenarios"])

    dataset = client.get_or_create_dataset("po-scenarios-all")
    dataset.insert(all_scenarios)
    print(f"Synced {len(all_scenarios)} scenarios to Opik dataset 'po-scenarios-all'")

    # Also create per-category datasets
    categories = set(s["category"] for s in all_scenarios)
    for cat in categories:
        cat_scenarios = [s for s in all_scenarios if s["category"] == cat]
        ds = client.get_or_create_dataset(f"po-scenarios-{cat}")
        ds.insert(cat_scenarios)
        print(f"  Synced {len(cat_scenarios)} scenarios to 'po-scenarios-{cat}'")


if __name__ == "__main__":
    sync()
