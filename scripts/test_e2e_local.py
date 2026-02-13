"""Local end-to-end test: simulate webhook → full workflow → real email + sheet row.

Usage:
    uv run python scripts/test_e2e_local.py

This script:
1. Builds the real workflow (OpenAI LLM + Tesseract OCR + Composio tools)
2. Loads a real PDF fixture (PO-2025-001)
3. Invokes the full workflow as if a webhook arrived
4. Sends a real confirmation email to the test recipient
5. Appends a real row to the Google Sheet

Requires .env with: OPENAI_API_KEY, COMPOSIO_API_KEY, COMPOSIO_USER_ID, SPREADSHEET_ID, SHEET_NAME
"""
# ruff: noqa: E402
import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(Path(project_root) / ".env")

from src.config import AppConfig
from src.builder import WorkflowBuilder

FIXTURE_PDF = Path(project_root) / "evals" / "fixtures" / "happy_path" / "complete_01.pdf"
TEST_RECIPIENT = "albertomartingarre@gmail.com"


def main():
    print("=== PO Agent — Local E2E Test ===\n")

    # 1. Build workflow with real services
    config = AppConfig.from_yaml(Path(project_root) / "config.yaml")
    print(f"Config: tool_manager={config.tool_manager}, llm={config.llm_model}")
    print(f"Spreadsheet: {config.spreadsheet_id[:20]}..., Sheet: {config.sheet_name}")

    builder = WorkflowBuilder(config)
    workflow = builder.build()
    print("Workflow built successfully.\n")

    # 2. Load PDF fixture
    pdf_bytes = FIXTURE_PDF.read_bytes()
    print(f"Loaded PDF fixture: {FIXTURE_PDF.name} ({len(pdf_bytes)} bytes)\n")

    # 3. Simulate webhook input state
    input_state = {
        "email_subject": "PO-2025-001 — Purchase Order from Acme Logistics",
        "email_body": (
            "Dear supplier,\n\n"
            "Please find attached our purchase order PO-2025-001.\n"
            "We need delivery to Retail Hub B, 456 Market St, Barcelona "
            "by January 18, 2025 at 08:00.\n\n"
            "Best regards,\nAlberto Martin\nAcme Logistics Ltd."
        ),
        "email_sender": TEST_RECIPIENT,
        "email_message_id": "e2e-test-local-001",
        "has_attachment": True,
        "pdf_bytes": pdf_bytes,
        "thread_id": None,
        "actions_log": [],
        "trajectory": [],
    }

    # 4. Invoke workflow
    print("Invoking workflow (classify → extract → validate → track → notify → report)...")
    print("This may take 30-60 seconds (OCR + multiple LLM calls + Composio API)...\n")

    result = workflow.invoke(input_state)

    # 5. Print results
    print("=" * 60)
    print("WORKFLOW RESULT")
    print("=" * 60)
    print(f"  Final status:    {result.get('final_status')}")
    print(f"  PO ID:           {result.get('po_id')}")
    print(f"  Is valid PO:     {result.get('is_valid_po')}")
    print(f"  Trajectory:      {result.get('trajectory')}")
    print(f"  Missing fields:  {result.get('missing_fields')}")
    print(f"  Sheet row added: {result.get('sheet_row_added')}")
    print(f"  Email sent:      {result.get('confirmation_email_sent')}")
    print(f"  Error:           {result.get('error_message')}")

    extracted = result.get("extracted_data")
    if extracted:
        print("\n  Extracted data:")
        for k, v in extracted.items():
            print(f"    {k}: {v}")

    print("\n" + "=" * 60)

    if result.get("final_status") == "completed":
        print(f"SUCCESS — Confirmation email sent to {TEST_RECIPIENT}")
        print("SUCCESS — Row appended to Google Sheet")
    elif result.get("final_status") == "error":
        print(f"ERROR — {result.get('error_message')}")
    else:
        print(f"Status: {result.get('final_status')}")


if __name__ == "__main__":
    main()
