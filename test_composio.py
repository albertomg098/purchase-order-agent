from composio import Composio
import json

composio = Composio(
    api_key="ak_a_DCr19b4O2QeUPGPu-v",
    toolkit_versions={
        "gmail": "20251027_00",
        "googlesheets": "20251027_00",
    }
)
USER_ID = "pg-test-18df6d41-8575-40f9-86d1-42d7c48f5b5c"
SPREADSHEET_ID="1i5SAthMfynT5p4mPmq-c_Iwl3SHU1vM1WG1nqZlvLjo"

# # Test 1: Fetch 1 email
# print("=== Test 1: Fetch emails ===")
# try:
#     result = composio.tools.execute(
#         "GMAIL_FETCH_EMAILS",
#         user_id=USER_ID,
#         arguments={"max_results": 1}
#     )
#     print(json.dumps(result, indent=2, default=str)[:500])
#     print("✅ Gmail OK")
# except Exception as e:
#     print(f"❌ Gmail failed: {e}")

# # Test 2: Sheets info
# print("\n=== Test 2: Google Sheets ===")
# try:
#     result = composio.tools.execute(
#         "GOOGLESHEETS_GET_SPREADSHEET_INFO",
#         user_id=USER_ID,
#         arguments={"spreadsheet_id": SPREADSHEET_ID}
#     )
#     print(json.dumps(result, indent=2, default=str)[:500])
#     print("✅ Sheets OK")
# except Exception as e:
#     print(f"❌ Sheets failed: {e}")
#
tools = composio.tools.get(user_id=USER_ID, toolkits=["googlesheets"])
for t in tools:
    name = t.get("function", {}).get("name", "unknown")
    print(f"  - {name}")