"""
scratch/sync_all_sent_emails.py
---------------------------------
Syncs ALL 142 sent outreach emails from data/sent_log.csv to the
"Yash Manglani" tab of the Google Sheet in batch mode (avoiding 429 rate limits).
"""

import sys
import os
import csv
import time
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from outreach.google_sheets_tracker import (
    _load_credentials, _get_target_worksheet, _ensure_headers,
    COLUMNS, SPREADSHEET_ID, TARGET_TAB_NAME, _format_exception
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SyncSentEmails")

def sync_sent_emails():
    print("=" * 65)
    print(" BATCH SYNCING ALL SENT EMAILS TO GOOGLE SHEET ('Yash Manglani' TAB) ")
    print("=" * 65)

    sent_log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sent_log.csv")
    buyers_csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "buyers.csv")

    if not os.path.exists(sent_log_path):
        print(f"[FAIL] Sent log file not found at: {sent_log_path}")
        return

    # 1. Load website lookup map from buyers.csv
    website_map = {}
    if os.path.exists(buyers_csv_path):
        try:
            with open(buyers_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    em = row.get("email", "").strip().lower()
                    web = row.get("website", "").strip()
                    if em and web:
                        website_map[em] = web
        except Exception as e:
            print(f"[WARNING] Could not read buyers.csv for websites: {e}")

    # 2. Load all SENT email records from sent_log.csv
    sent_records = []
    seen_sent_emails = set()

    with open(sent_log_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get("status", "").strip().lower()
            email = row.get("email", "").strip()
            if status == "sent" and email:
                email_lower = email.lower()
                if email_lower not in seen_sent_emails:
                    seen_sent_emails.add(email_lower)
                    company = row.get("company_name", "").strip()
                    sent_date = row.get("sent_date", "").strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    website = website_map.get(email_lower, "")
                    
                    sent_records.append({
                        "email": email,
                        "company_name": company,
                        "sent_date": sent_date,
                        "website": website
                    })

    print(f"\nFound {len(sent_records)} unique successfully sent email records to sync to Google Sheet.")

    if not sent_records:
        print("[INFO] No sent email records found to sync.")
        return

    # 3. Connect to Google Sheets API
    try:
        import gspread
        creds = _load_credentials()
        client = gspread.authorize(creds)
        
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", SPREADSHEET_ID)
        spreadsheet = client.open_by_key(spreadsheet_id)
        print(f"Opened Spreadsheet: '{spreadsheet.title}' (ID: {spreadsheet_id})")

        worksheet = _get_target_worksheet(spreadsheet)
        print(f"Target Worksheet: '{worksheet.title}'")

        col_map = _ensure_headers(worksheet)
        print(f"Header Map: {col_map}")

    except Exception as e:
        detailed = _format_exception(e)
        print(f"[FAIL] Could not connect to Google Sheets: {detailed}")
        return

    # 4. Fetch existing sheet data
    email_col    = col_map.get("EMAIL ADDRESS",       COLUMNS["EMAIL ADDRESS"])
    date_col     = col_map.get("DATE",                COLUMNS["DATE"])
    name_col     = col_map.get("NAME OF THE COMPANY", COLUMNS["NAME OF THE COMPANY"])
    website_col  = col_map.get("WEBSITE LINK",        COLUMNS["WEBSITE LINK"])
    response_col = col_map.get("RESPONSES",           COLUMNS["RESPONSES"])
    feedback_col = col_map.get("INTERN'S FEEDBACK",   COLUMNS["INTERN'S FEEDBACK"])

    print("\nFetching existing sheet rows...")
    all_email_values = worksheet.col_values(email_col)
    all_feedback_values = worksheet.col_values(feedback_col)

    existing_row_index = {}
    for idx, val in enumerate(all_email_values):
        if idx == 0:
            continue
        val_clean = val.strip().lower()
        if val_clean:
            existing_row_index[val_clean] = idx + 1

    batch_updates = []
    new_rows_to_append = []

    for rec in sent_records:
        email = rec["email"]
        email_lower = email.lower()
        company = rec["company_name"]
        website = rec["website"]
        sent_date = rec["sent_date"]

        if email_lower in existing_row_index:
            row_num = existing_row_index[email_lower]
            current_feedback = ""
            if row_num <= len(all_feedback_values):
                current_feedback = all_feedback_values[row_num - 1]

            batch_updates.extend([
                {"range": gspread.utils.rowcol_to_a1(row_num, date_col), "values": [[sent_date]]},
                {"range": gspread.utils.rowcol_to_a1(row_num, name_col), "values": [[company]]},
                {"range": gspread.utils.rowcol_to_a1(row_num, email_col), "values": [[email]]},
                {"range": gspread.utils.rowcol_to_a1(row_num, website_col), "values": [[website]]},
                {"range": gspread.utils.rowcol_to_a1(row_num, response_col), "values": [["Sent"]]},
                {"range": gspread.utils.rowcol_to_a1(row_num, feedback_col), "values": [[current_feedback]]},
            ])
        else:
            max_col = max(COLUMNS.values())
            new_row = [""] * max_col
            new_row[date_col - 1] = sent_date
            new_row[name_col - 1] = company
            new_row[email_col - 1] = email
            new_row[website_col - 1] = website
            new_row[response_col - 1] = "Sent"
            new_row[feedback_col - 1] = ""
            new_rows_to_append.append(new_row)

    print(f"\nExecuting Batch Updates: {len(batch_updates)} cell updates for existing rows...")
    if batch_updates:
        chunk_size = 500
        for i in range(0, len(batch_updates), chunk_size):
            chunk = batch_updates[i:i + chunk_size]
            worksheet.batch_update(chunk)
            print(f"  - Batch update chunk {i//chunk_size + 1}/{(len(batch_updates)-1)//chunk_size + 1} completed.")
            time.sleep(1)

    print(f"Executing Batch Appends: {len(new_rows_to_append)} new rows to append...")
    if new_rows_to_append:
        worksheet.append_rows(new_rows_to_append, value_input_option="USER_ENTERED")
        print(f"  - Successfully appended {len(new_rows_to_append)} new rows.")

    print("\n" + "=" * 65)
    print(" SYNC SUMMARY ")
    print("=" * 65)
    print(f"  Total Sent Emails Processed : {len(sent_records)}")
    print(f"  Updated Existing Rows       : {len(batch_updates) // 6}")
    print(f"  Appended New Rows           : {len(new_rows_to_append)}")
    print("=============================================================")
    print("ALL SENT EMAILS BATCH-SYNCED TO GOOGLE SHEET SUCCESSFULLY!")

if __name__ == "__main__":
    sync_sent_emails()
