"""
outreach/google_sheets_tracker.py
----------------------------------
Automatically tracks successfully sent outreach emails in the Google Sheet.

Target Sheet: https://docs.google.com/spreadsheets/d/1TpqpbO9_cYFGDcFqIVidmvJR2lm5ply4ok-TFmP6H_I/edit
Target Tab:   "Yash Manglani"  (matched using .strip() and .lower() for trailing/leading spaces)

COLUMN MAPPING:
    A - DATE
    B - NAME OF THE COMPANY
    C - EMAIL ADDRESS
    D - WEBSITE LINK
    E - RESPONSES
    F - INTERN'S FEEDBACK

RULES:
  - Only called for successfully sent emails (status == "Sent")
  - Deduplicates by EMAIL ADDRESS (case-insensitive, normalized)
  - If email already exists in sheet -> update that row, preserve existing INTERN'S FEEDBACK
  - If email is new -> append a new row
  - Uses bulk batch operations (append_rows & batch_update) to avoid HTTP 429 rate limit errors
"""

import os
import json
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Column definitions (1-indexed for gspread) ─────────────────────────────
COLUMNS = {
    "DATE": 1,
    "NAME OF THE COMPANY": 2,
    "EMAIL ADDRESS": 3,
    "WEBSITE LINK": 4,
    "RESPONSES": 5,
    "INTERN'S FEEDBACK": 6,
}
EXPECTED_HEADERS = list(COLUMNS.keys())

TARGET_TAB_NAME = "Yash Manglani"
SPREADSHEET_ID = "1TpqpbO9_cYFGDcFqIVidmvJR2lm5ply4ok-TFmP6H_I"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def _format_exception(e):
    """Format exception details cleanly for Google Sheets API errors."""
    if hasattr(e, 'response') and getattr(e, 'response', None) is not None:
        resp = e.response
        status = getattr(resp, 'status_code', getattr(resp, 'status', ''))
        text = getattr(resp, 'text', getattr(resp, 'content', ''))
        if status or text:
            return f"HTTP [{status}] API Error: {text}"
            
    cause = getattr(e, '__cause__', None)
    if cause and str(cause).strip():
        return f"{type(e).__name__} (caused by {type(cause).__name__}: {cause})"
        
    err_str = str(e).strip()
    if err_str:
        return f"{type(e).__name__}: {err_str}"
        
    return f"{type(e).__name__}: {repr(e)}"


def _load_credentials():
    """Load Google Service Account credentials."""
    from google.oauth2.service_account import Credentials

    # Project root is two levels up from this file (outreach/google_sheets_tracker.py)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "").strip()
    if creds_file:
        # Resolve relative paths against the project root so the path works
        # regardless of the CWD from which the server or script is launched.
        if not os.path.isabs(creds_file):
            creds_file = os.path.join(base_dir, creds_file)
        if os.path.isfile(creds_file) and os.path.getsize(creds_file) > 0:
            logger.info(f"[SheetsTracker] Loading credentials from file: {creds_file}")
            return Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        else:
            logger.warning(
                f"[SheetsTracker] GOOGLE_SHEETS_CREDENTIALS_FILE set to '{creds_file}' "
                "but file not found or empty — falling back to auto-discovery."
            )

    for fname in ("credentials.json", "service_account.json"):
        candidate = os.path.join(base_dir, fname)
        if os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
            logger.info(f"[SheetsTracker] Loading credentials from file: {candidate}")
            return Credentials.from_service_account_file(candidate, scopes=SCOPES)

    raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw_json:
        logger.info("[SheetsTracker] Loading credentials from GOOGLE_SERVICE_ACCOUNT_JSON env var.")
        try:
            info = json.loads(raw_json)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"GOOGLE_SERVICE_ACCOUNT_JSON is invalid JSON: {e}")
        return Credentials.from_service_account_info(info, scopes=SCOPES)

    raise RuntimeError(
        "Google Sheets credentials not found. "
        f"Looked for credentials.json / service_account.json in: {base_dir}. "
        "Set GOOGLE_SHEETS_CREDENTIALS_FILE in .env to the correct path."
    )


def _get_target_worksheet(spreadsheet):
    """Return worksheet matching 'Yash Manglani' (trimmed, case-insensitive)."""
    target_clean = TARGET_TAB_NAME.strip().lower()
    for ws in spreadsheet.worksheets():
        if ws.title.strip().lower() == target_clean:
            return ws
            
    available = [repr(ws.title) for ws in spreadsheet.worksheets()]
    raise ValueError(f"Tab '{TARGET_TAB_NAME}' not found in spreadsheet. Available tabs: {available}")


def _ensure_headers(worksheet):
    """Check that row 1 contains expected column headers."""
    first_row = worksheet.row_values(1)

    if not any(cell.strip() for cell in first_row):
        worksheet.update(range_name="A1", values=[EXPECTED_HEADERS])
        logger.info("[SheetsTracker] Headers written to row 1 of 'Yash Manglani' tab.")
        return {h: i + 1 for i, h in enumerate(EXPECTED_HEADERS)}

    col_map = {}
    for idx, cell in enumerate(first_row):
        cleaned = cell.strip()
        if cleaned in EXPECTED_HEADERS:
            col_map[cleaned] = idx + 1

    for header, fixed_col in COLUMNS.items():
        if header not in col_map:
            col_map[header] = fixed_col

    return col_map


def _find_email_row(worksheet, email: str, email_col: int):
    """Return 1-based row number where EMAIL ADDRESS matches (case-insensitive)."""
    email_values = worksheet.col_values(email_col)
    email_lower = email.strip().lower()
    for row_idx, cell_val in enumerate(email_values):
        if row_idx == 0:
            continue
        if cell_val.strip().lower() == email_lower:
            return row_idx + 1
    return None


def track_sent_email_to_sheets(
    email: str,
    company_name: str,
    website: str = "",
    sent_timestamp: str = "",
) -> tuple[bool, str]:
    """Record a successfully sent outreach email in the Google Sheet."""
    try:
        import gspread
    except ImportError:
        msg = "[SheetsTracker] 'gspread' library not installed."
        logger.error(msg)
        return False, msg

    if not sent_timestamp:
        sent_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        creds = _load_credentials()
        client = gspread.authorize(creds)
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", SPREADSHEET_ID)
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = _get_target_worksheet(spreadsheet)
        col_map = _ensure_headers(worksheet)

        email_col    = col_map.get("EMAIL ADDRESS",       COLUMNS["EMAIL ADDRESS"])
        date_col     = col_map.get("DATE",                COLUMNS["DATE"])
        name_col     = col_map.get("NAME OF THE COMPANY", COLUMNS["NAME OF THE COMPANY"])
        website_col  = col_map.get("WEBSITE LINK",        COLUMNS["WEBSITE LINK"])
        response_col = col_map.get("RESPONSES",           COLUMNS["RESPONSES"])
        feedback_col = col_map.get("INTERN'S FEEDBACK",   COLUMNS["INTERN'S FEEDBACK"])

        existing_row = _find_email_row(worksheet, email, email_col)

        row_data = {
            "DATE": sent_timestamp,
            "NAME OF THE COMPANY": company_name.strip() if company_name else "",
            "EMAIL ADDRESS": email.strip(),
            "WEBSITE LINK": website.strip() if website else "",
            "RESPONSES": "Sent",
            "INTERN'S FEEDBACK": "",
        }

        if existing_row is not None:
            updates = [
                {"range": gspread.utils.rowcol_to_a1(existing_row, date_col), "values": [[row_data["DATE"]]]},
                {"range": gspread.utils.rowcol_to_a1(existing_row, name_col), "values": [[row_data["NAME OF THE COMPANY"]]]},
                {"range": gspread.utils.rowcol_to_a1(existing_row, email_col), "values": [[row_data["EMAIL ADDRESS"]]]},
                {"range": gspread.utils.rowcol_to_a1(existing_row, website_col), "values": [[row_data["WEBSITE LINK"]]]},
                {"range": gspread.utils.rowcol_to_a1(existing_row, response_col), "values": [[row_data["RESPONSES"]]]},
            ]
            worksheet.batch_update(updates)
            msg = f"[SheetsTracker] Updated existing row {existing_row} for email: {email}"
            logger.info(msg)
            return True, msg
        else:
            max_col = max(COLUMNS.values())
            new_row = [""] * max_col
            new_row[date_col - 1] = row_data["DATE"]
            new_row[name_col - 1] = row_data["NAME OF THE COMPANY"]
            new_row[email_col - 1] = row_data["EMAIL ADDRESS"]
            new_row[website_col - 1] = row_data["WEBSITE LINK"]
            new_row[response_col - 1] = row_data["RESPONSES"]
            new_row[feedback_col - 1] = row_data["INTERN'S FEEDBACK"]
            worksheet.append_row(new_row, value_input_option="USER_ENTERED")
            msg = f"[SheetsTracker] Appended new row for email: {email}"
            logger.info(msg)
            return True, msg

    except Exception as e:
        detailed_error = _format_exception(e)
        error_msg = f"[SheetsTracker] Google Sheets update failed for {email}: {detailed_error}"
        logger.error(error_msg)
        return False, error_msg


def bulk_sync_to_sheets(buyers: list) -> dict:
    """
    Full-sync ALL buyers from local database to Google Sheet tab 'Yash Manglani' using
    batched operations to avoid HTTP 429 rate limit errors.
    """
    result = {
        "success": False,
        "synced": 0,
        "failed": 0,
        "skipped": 0,
        "errors": [],
        "message": "",
    }

    try:
        import gspread
    except ImportError:
        msg = "'gspread' library not installed."
        logger.error(f"[SheetsTracker] {msg}")
        result["message"] = msg
        return result

    try:
        creds = _load_credentials()
        client = gspread.authorize(creds)
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", SPREADSHEET_ID)
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = _get_target_worksheet(spreadsheet)
        col_map = _ensure_headers(worksheet)

        email_col    = col_map.get("EMAIL ADDRESS",       COLUMNS["EMAIL ADDRESS"])
        date_col     = col_map.get("DATE",                COLUMNS["DATE"])
        name_col     = col_map.get("NAME OF THE COMPANY", COLUMNS["NAME OF THE COMPANY"])
        website_col  = col_map.get("WEBSITE LINK",        COLUMNS["WEBSITE LINK"])
        response_col = col_map.get("RESPONSES",           COLUMNS["RESPONSES"])
        feedback_col = col_map.get("INTERN'S FEEDBACK",   COLUMNS["INTERN'S FEEDBACK"])

        all_email_values = worksheet.col_values(email_col)
        existing_email_index = {}
        for row_idx, cell_val in enumerate(all_email_values):
            if row_idx == 0:
                continue
            if cell_val.strip():
                existing_email_index[cell_val.strip().lower()] = row_idx + 1

        all_feedback_values = worksheet.col_values(feedback_col)

        batch_updates = []
        new_rows_to_append = []

        for buyer in buyers:
            email = (buyer.get("email") or "").strip()
            if not email:
                result["skipped"] += 1
                continue

            company_name = (buyer.get("company_name") or "").strip()
            website      = (buyer.get("website") or "").strip()
            date_val     = (buyer.get("discovered_date") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            validation   = (buyer.get("validation_status") or "").strip()
            # When syncing sent emails, validation_status is already "Sent".
            # For buyer-discovery records, map "Valid Format" → "Discovered".
            if validation.lower() == "sent":
                response_val = "Sent"
            elif validation == "Valid Format":
                response_val = "Discovered"
            else:
                response_val = validation or "Discovered"

            email_lower = email.lower()

            if email_lower in existing_email_index:
                existing_row = existing_email_index[email_lower]
                current_feedback = ""
                if existing_row <= len(all_feedback_values):
                    current_feedback = all_feedback_values[existing_row - 1]

                batch_updates.extend([
                    {"range": gspread.utils.rowcol_to_a1(existing_row, date_col), "values": [[date_val]]},
                    {"range": gspread.utils.rowcol_to_a1(existing_row, name_col), "values": [[company_name]]},
                    {"range": gspread.utils.rowcol_to_a1(existing_row, email_col), "values": [[email]]},
                    {"range": gspread.utils.rowcol_to_a1(existing_row, website_col), "values": [[website]]},
                    {"range": gspread.utils.rowcol_to_a1(existing_row, response_col), "values": [[response_val]]},
                    {"range": gspread.utils.rowcol_to_a1(existing_row, feedback_col), "values": [[current_feedback]]},
                ])
                result["synced"] += 1
            else:
                max_col = max(COLUMNS.values())
                new_row = [""] * max_col
                new_row[date_col     - 1] = date_val
                new_row[name_col     - 1] = company_name
                new_row[email_col    - 1] = email
                new_row[website_col  - 1] = website
                new_row[response_col - 1] = response_val
                new_row[feedback_col - 1] = ""
                new_rows_to_append.append(new_row)
                existing_email_index[email_lower] = len(all_email_values) + len(new_rows_to_append)
                result["synced"] += 1

        # Execute single batch update for existing rows
        if batch_updates:
            # Batch update in chunks of 500 range objects
            chunk_size = 500
            for i in range(0, len(batch_updates), chunk_size):
                chunk = batch_updates[i:i + chunk_size]
                worksheet.batch_update(chunk)
                time.sleep(1)

        # Execute single append_rows for all new rows
        if new_rows_to_append:
            worksheet.append_rows(new_rows_to_append, value_input_option="USER_ENTERED")

        skip_note = f", {result['skipped']} skipped (no email)." if result["skipped"] else "."
        result["success"] = True
        result["message"] = f"Google Sheet updated successfully — {result['synced']} buyer(s) synced{skip_note}"

    except Exception as e:
        detailed_error = _format_exception(e)
        err_msg = f"Google Sheets bulk sync failed: {detailed_error}"
        logger.error(f"[SheetsTracker] {err_msg}")
        result["message"] = err_msg
        result["errors"].append(err_msg)

    return result
