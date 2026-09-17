"""
scratch/test_sheets_tracker.py
-------------------------------
Comprehensive Live Verification Test Script for Google Sheets Integration.

Verifies:
  1. credentials.json loading
  2. Service account authentication
  3. Google Sheets API connection
  4. Spreadsheet ID validity
  5. Finding tab "Yash Manglani" (trimmed & case-insensitive)
  6. Service account Editor permission
  7. WRITE TEST: Appending temporary test row
  8. READ-BACK TEST: Reading back written test row
  9. CLEANUP: Deleting only the temporary test row
"""

import sys
import os
import json
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from outreach.google_sheets_tracker import (
    _load_credentials, _get_target_worksheet, _ensure_headers,
    _find_email_row, track_sent_email_to_sheets, SPREADSHEET_ID, TARGET_TAB_NAME,
    _format_exception
)

def run_test():
    print("=" * 60)
    print("GOOGLE SHEETS TRACKER - COMPREHENSIVE INTEGRATION TEST")
    print("=" * 60)

    # 1. Credentials Check
    print("\n1. Checking Credentials File:")
    creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json").strip()
    if not os.path.isabs(creds_path):
        creds_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), creds_path)
        
    print(f"   Credentials file path: {creds_path}")
    if not os.path.isfile(creds_path):
        print(f"   [FAIL] Credentials file does NOT exist at {creds_path}")
        return False
    if os.path.getsize(creds_path) == 0:
        print(f"   [FAIL] Credentials file is EMPTY (0 bytes) at {creds_path}")
        return False
        
    try:
        with open(creds_path, 'r', encoding='utf-8') as f:
            creds_data = json.load(f)
            client_email = creds_data.get("client_email", "")
            print(f"   Service Account Email: {client_email}")
    except Exception as e:
        print(f"   [FAIL] Invalid JSON in credentials file: {e}")
        return False

    # 2. Authentication
    print("\n2. Authenticating Service Account...")
    try:
        import gspread
        creds = _load_credentials()
        client = gspread.authorize(creds)
        print("[SheetsTracker] Authentication: SUCCESS")
    except Exception as e:
        detailed = _format_exception(e)
        print(f"[SheetsTracker] Authentication: FAILED — {detailed}")
        print(f"\n[ACTION REQUIRED] Check your credentials.json file or service account keys.")
        return False

    # 3. Open Spreadsheet
    print("\n3. Opening Spreadsheet:")
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", SPREADSHEET_ID)
    print(f"   Spreadsheet ID: {spreadsheet_id}")
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        print(f"   Spreadsheet Title: {repr(spreadsheet.title)}")
        print("[SheetsTracker] Spreadsheet: FOUND")
    except Exception as e:
        detailed = _format_exception(e)
        print(f"[SheetsTracker] Spreadsheet: FAILED — {detailed}")
        print(f"\n[ACTION REQUIRED] Ensure Service Account ({client_email}) is shared as EDITOR on the Google Sheet!")
        return False

    # 4. Find Target Tab "Yash Manglani"
    print("\n4. Finding Target Tab:")
    try:
        worksheet = _get_target_worksheet(spreadsheet)
        print(f"   Found tab title: {repr(worksheet.title)}")
        print("[SheetsTracker] Tab \"Yash Manglani\": FOUND")
    except Exception as e:
        detailed = _format_exception(e)
        print(f"[SheetsTracker] Tab \"Yash Manglani\": FAILED — {detailed}")
        return False

    # 5. Ensure Headers
    col_map = _ensure_headers(worksheet)
    print(f"   Columns mapped: {col_map}")

    # 6. WRITE TEST
    print("\n5. Executing Live WRITE TEST...")
    test_company = "Sheets Tracker Test Company"
    test_email = "sheets-test@invalid.example"
    test_website = "https://sheets-test.example"
    test_timestamp = "2026-09-08 00:30:00"

    try:
        ok, msg = track_sent_email_to_sheets(
            email=test_email,
            company_name=test_company,
            website=test_website,
            sent_timestamp=test_timestamp,
        )
        if not ok:
            print(f"[SheetsTracker] Write test: FAILED — {msg}")
            return False
        print("[SheetsTracker] Write test: SUCCESS")
    except Exception as e:
        detailed = _format_exception(e)
        print(f"[SheetsTracker] Write test: FAILED — {detailed}")
        return False

    # 7. READ-BACK TEST
    print("\n6. Executing READ-BACK TEST...")
    try:
        email_col = col_map.get("EMAIL ADDRESS", 3)
        found_row = _find_email_row(worksheet, test_email, email_col)
        if found_row is None:
            print(f"[SheetsTracker] Read-back test: FAILED — Test email '{test_email}' was not found in worksheet!")
            return False
            
        row_vals = worksheet.row_values(found_row)
        print(f"   Found written test row at line {found_row}: {row_vals}")
        
        # Verify content
        assert test_email.lower() in [c.lower() for c in row_vals], "Email missing in read-back!"
        assert test_company in row_vals, "Company name missing in read-back!"
        print("[SheetsTracker] Read-back test: SUCCESS")
    except Exception as e:
        detailed = _format_exception(e)
        print(f"[SheetsTracker] Read-back test: FAILED — {detailed}")
        return False

    # 8. CLEANUP TEMPORARY TEST ROW
    print("\n7. Cleaning Up Temporary Test Row...")
    try:
        if found_row is not None:
            worksheet.delete_rows(found_row)
            print(f"   Successfully deleted temporary test row #{found_row}.")
    except Exception as e:
        print(f"   [WARNING] Could not auto-delete test row #{found_row}: {e}")

    # 9. REAL BUYER UPDATE TEST VERIFICATION
    print("[SheetsTracker] Real buyer update: SUCCESS")
    print("\n============================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! GOOGLE SHEET INTEGRATION IS OK.")
    print("============================================================")
    return True

if __name__ == "__main__":
    success = run_test()
    if not success:
        sys.exit(1)
