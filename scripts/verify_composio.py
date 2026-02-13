"""Quick verification script: test Composio send_email and append_sheet_row.

Usage:
    uv run python scripts/verify_composio.py

Reads COMPOSIO_API_KEY, COMPOSIO_USER_ID, SPREADSHEET_ID, SHEET_NAME from .env.
"""
import sys
from datetime import datetime, timezone

from src.config import AppConfig
from src.services.tools.composio import ComposioToolManager


def main():
    config = AppConfig.from_yaml("config.yaml")

    if not config.composio_api_key:
        print("ERROR: COMPOSIO_API_KEY not set in .env")
        sys.exit(1)

    if not config.spreadsheet_id:
        print("ERROR: SPREADSHEET_ID not set in .env")
        sys.exit(1)

    mgr = ComposioToolManager(
        api_key=config.composio_api_key,
        user_id=config.composio_user_id,
        toolkit_versions=config.composio_toolkit_versions,
        sheet_name=config.sheet_name,
    )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 1. Test append_sheet_row
    print(f"[1/2] Appending test row to spreadsheet {config.spreadsheet_id}...")
    try:
        row_result = mgr.append_sheet_row(
            spreadsheet_id=config.spreadsheet_id,
            values=["TEST-PO-001", "Verification Script", ts, "test", "ok"],
        )
        print(f"  OK: {row_result}")
    except Exception as e:
        print(f"  FAIL: {e}")

    # 2. Test send_email
    recipient = input("\nRecipient email for test (or press Enter to skip): ").strip()
    if recipient:
        print(f"[2/2] Sending test email to {recipient}...")
        try:
            email_result = mgr.send_email(
                to=recipient,
                subject=f"PO Agent Verification - {ts}",
                body=f"This is a test email from the PO Agent verification script.\n\nTimestamp: {ts}",
            )
            print(f"  OK: {email_result}")
        except Exception as e:
            print(f"  FAIL: {e}")
    else:
        print("[2/2] Skipped email test.")

    print("\nDone.")


if __name__ == "__main__":
    main()
