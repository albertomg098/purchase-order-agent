"""Manual verification script for Composio connections.

Usage:
    uv run python scripts/test_composio.py

Requires .env with:
    COMPOSIO_API_KEY, COMPOSIO_USER_ID, SPREADSHEET_ID
"""
# ruff: noqa: E402
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(project_root) / ".env")

from src.services.tools.composio import ComposioToolManager

API_KEY = os.environ.get("COMPOSIO_API_KEY")
USER_ID = os.environ.get("COMPOSIO_USER_ID", "default")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")
SHEET_NAME = os.environ.get("SHEET_NAME", "Sheet1")

TOOLKIT_VERSIONS = {
    "gmail": "20251027_00",
    "googlesheets": "20251027_00",
}


def main():
    if not API_KEY:
        print("ERROR: COMPOSIO_API_KEY not set in .env")
        sys.exit(1)

    print(f"Composio user_id: {USER_ID}")
    print(f"Spreadsheet ID:   {SPREADSHEET_ID[:20]}..." if SPREADSHEET_ID else "Spreadsheet ID: (not set)")
    print()

    mgr = ComposioToolManager(
        api_key=API_KEY,
        user_id=USER_ID,
        toolkit_versions=TOOLKIT_VERSIONS,
        sheet_name=SHEET_NAME,
    )

    # Test 1: Send a test email
    print("=== Test 1: Send email ===")
    try:
        result = mgr.send_email(
            to="alberto.martin.martinmoreno@gmail.com",
            subject="[PO Agent] Composio test email",
            body="This is a test email sent by the PO Agent verification script.",
        )
        print(f"  Result: {result}")
        print("  OK")
    except Exception as e:
        print(f"  FAILED: {e}")

    # Test 2: Append a test row to Google Sheet
    print("\n=== Test 2: Append sheet row ===")
    if not SPREADSHEET_ID:
        print("  SKIPPED (no SPREADSHEET_ID)")
    else:
        try:
            result = mgr.append_sheet_row(
                spreadsheet_id=SPREADSHEET_ID,
                values=["TEST-PO-001", "Test Customer", "Warehouse A", "Customer HQ", "2026-02-15", "John Doe", "+1234567890", "test"],
            )
            print(f"  Result: {result}")
            print("  OK")
        except Exception as e:
            print(f"  FAILED: {e}")

    # Test 3: Fetch a message (use a known message_id or skip)
    print("\n=== Test 3: Fetch email message ===")
    print("  (Requires a known message_id — skipping automated test)")
    print("  To test manually, call: mgr.get_email_message(message_id='<your-msg-id>')")

    print("\n=== All tests complete ===")


if __name__ == "__main__":
    main()
