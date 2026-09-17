import os
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

import config
from search.searxng import searxng_search_buyers
from search.volza import volza_search_buyers
from search.trademo import trademo_search_buyers
from search.linkedin import search_linkedin_buyers
from search.facebook import facebook_search_buyers
from scraper.website_scraper import scrape_website_emails
from processing.cleaner import clean_buyer_data
from processing.validator import validate_email
from processing.duplicate_checker import remove_duplicates, load_existing_emails, load_sent_log_emails, merge_buyers

from ai.classifier import classify_contact
from outreach.gmail_sender import send_email
from outreach.google_sheets_tracker import bulk_sync_to_sheets
from search.discovery_engine import run_multi_query_buyer_discovery

# Persistent Database & 24/7 Cloud Background Worker
from worker.db import (
    init_db,
    save_buyers_to_db,
    read_all_buyers_from_db,
    get_worker_status,
    get_search_history,
    record_search_history
)
from worker.scheduler import (
    init_scheduler,
    trigger_manual_discovery,
    set_search_interval
)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Ensure data directory and SQLite DB are initialized
os.makedirs(os.path.dirname(config.BUYERS_CSV_PATH), exist_ok=True)
init_db()

# Initialize 24/7 Cloud Background Scheduler (Default: Every 6 hours)
try:
    init_scheduler(interval_hours=6)
except Exception as e:
    print(f"[App] Scheduler startup notice: {e}")

# Shortened Email Template for Authentic Handmade Himalayan Singing Bowls by OM Enterprise
DEFAULT_EMAIL_TEMPLATE = """Subject: Wholesale Himalayan Singing Bowls – OM Enterprise

Dear {{name}},

We came across {{company}} while researching Singing Bowl businesses in {{country}}.

We are a Nepal-based manufacturer/exporter of authentic handmade Himalayan Singing Bowls, offering wholesale and private-label options.

I’ve attached our product catalogue for your review.

If you are interested, I’d be happy to share wholesale pricing and shipping details.

Kind Regards,
Yash Manglani
Sales Executive
OM Enterprise
exportindia2026us@gmail.com
+91 80577 10065"""


def read_buyers_csv():
    """Helper function to load all buyers from SQLite DB (falls back to buyers.csv)"""
    try:
        buyers = read_all_buyers_from_db()
        if buyers:
            return buyers
    except Exception as e:
        print(f"[App] SQLite read fallback: {e}")
        
    buyers = []
    if os.path.exists(config.BUYERS_CSV_PATH):
        try:
            with open(config.BUYERS_CSV_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    buyers.append(dict(row))
        except Exception as e:
            print(f"[App] Error reading buyers.csv: {e}")
    return buyers

def write_buyers_csv(buyers_list):
    """Helper function to rewrite buyers into SQLite DB and data/buyers.csv"""
    try:
        save_buyers_to_db(buyers_list)
    except Exception as e:
        print(f"[App] SQLite write notice: {e}")

# ── API ENDPOINTS FOR CLOUD WORKER & KEEP-ALIVE PINGS ──────────────────────

@app.route('/api/ping')
def ping():
    """24/7 Cloud Keep-Alive Endpoint for cron-job.org / UptimeRobot."""
    return jsonify({
        "status": "ok",
        "service": "api-export-buyer-search",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/api/worker/status')
def worker_status_api():
    """Returns live Worker Status and recent Search History JSON."""
    status_info = get_worker_status()
    history = get_search_history(limit=10)
    return jsonify({
        "worker_status": status_info,
        "search_history": history
    })

@app.route('/api/worker/trigger', methods=['POST'])
def trigger_worker_api():
    """Triggers an immediate background buyer discovery search."""
    data = request.get_json(silent=True) or request.form
    state = data.get('state', 'California').strip()
    try:
        limit = int(data.get('limit', 10))
    except (ValueError, TypeError):
        limit = 10
        
    trigger_manual_discovery(state=state, limit=limit)
    return jsonify({
        "status": "triggered",
        "message": f"Background search started for state '{state}'",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/api/worker/config', methods=['POST'])
def worker_config_api():
    """Configures the background worker interval in hours."""
    data = request.get_json(silent=True) or request.form
    try:
        hours = int(data.get('interval_hours', 6))
        if hours < 1:
            hours = 1
    except (ValueError, TypeError):
        hours = 6
        
    set_search_interval(hours)
    return jsonify({
        "status": "updated",
        "interval_hours": hours,
        "message": f"Background worker rescheduled for every {hours} hour(s)."
    })


@app.route('/')
def index():
    """Home Page - Buyer Search Form & API Status Overview"""
    api_status = {
        "searxng": bool(config.SEARXNG_URL),
        "gemini": bool(config.GEMINI_API_KEY),
        "gmail": bool(config.GMAIL_EMAIL and config.GMAIL_APP_PASSWORD)
    }
    status_info = get_worker_status()
    history = get_search_history(limit=5)
    return render_template('index.html', api_status=api_status, worker_status=status_info, history=history)

@app.route('/discover', methods=['POST'])
def discover():
    """Main Buyer Discovery Workflow Route (SearXNG + State target + Relevance Filter)"""
    keyword = request.form.get('keyword', '').strip()
    country = request.form.get('country', '').strip()
    state = request.form.get('state', 'California').strip()
    try:
        limit = int(request.form.get('limit', 10))
    except ValueError:
        limit = 10

    if not keyword or not country:
        flash("Please enter both a Product/Keyword and Country.", "warning")
        return redirect(url_for('index'))

    # Step 1: Run Multi-Query Discovery Engine across SearXNG with State target
    discovered_buyers, diag = run_multi_query_buyer_discovery(keyword, country, state=state, target_limit=limit)

    for lead in discovered_buyers:
        lead["classification"] = "Unclassified"
        lead["discovered_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Step 2: Merge with Existing Buyers in buyers.csv (Never delete existing buyers)
    existing_buyers = read_buyers_csv()
    updated_list, new_added_count, updated_count = merge_buyers(existing_buyers, discovered_buyers)
    write_buyers_csv(updated_list)

    # Step 3: Build Diagnostic Summary Flash Message & Timing Metrics
    pipeline_summary = (
        f"Validated emails: {diag.get('emails_validated', 0)} | "
        f"Validated new buyers: {diag.get('validated_new_buyers', 0)} | "
        f"Already existing buyers: {diag.get('already_existing_buyers', 0)} | "
        f"Final valid buyers added: {new_added_count}"
    )

    timing_summary = (
        f"Search time: {diag.get('search_time_sec', 0.0)}s | "
        f"Extraction time: {diag.get('extraction_time_sec', 0.0)}s | "
        f"Total time: {diag.get('total_time_sec', 0.0)}s"
    )

    diag_summary = (
        f"Queries: {diag['queries_executed']} | "
        f"SearXNG: {diag['searxng_results']} | "
        f"Relevance Rejected: {diag.get('relevance_rejected', 0)} | "
        f"Unique businesses: {diag['unique_businesses_found']} | "
        f"Websites: {diag['official_websites_found']} | "
        f"Emails found: {diag['emails_found']}"
    )

    reasons = diag.get("rejection_reasons", {})
    rejection_detail = (
        f"Rejections: {reasons.get('relevance_failed', 0)} low relevance site(s), "
        f"{reasons.get('no_official_website', 0)} non-official site(s), "
        f"{reasons.get('no_email_on_website', 0)} site(s) without email, "
        f"{reasons.get('email_validation_failed', 0)} email validation failed, "
        f"{reasons.get('already_in_database', 0)} already in database."
    )

    if new_added_count > 0 or diag.get('validated_new_buyers', 0) > 0:
        flash_type = "success"
        main_msg = f"Discovery Complete! Added {new_added_count} new valid buyer lead(s) ({updated_count} updated). Total saved buyers: {len(updated_list)}."
    elif diag.get('already_existing_buyers', 0) > 0:
        flash_type = "info"
        main_msg = f"Discovery Complete! Found {diag['already_existing_buyers']} valid buyer(s) that already exist in database."
    else:
        flash_type = "warning"
        loc_display = f"{state} {country}".strip()
        main_msg = f"0 New Valid Buyers returned for '{keyword}' in '{loc_display}'."

    full_flash_msg = f"{main_msg} [{pipeline_summary}] [{timing_summary}] [{diag_summary}] [{rejection_detail}]"
    flash(full_flash_msg, flash_type)
    return redirect(url_for('buyers'))


def sort_buyers_by_priority(buyer_list):
    """
    Prioritizes buyers according to validity and discovery recency:
    1. Valid buyers with email address -> TOP (newest discovered_date first)
    2. Older valid buyers -> BELOW
    3. Invalid buyers -> placed at the bottom
    """
    valid_buyers = []
    invalid_buyers = []
    
    for b in buyer_list:
        if not b.get("discovered_date"):
            b["discovered_date"] = "2026-01-01 00:00:00"
            
        is_valid = (b.get("validation_status") == "Valid Format") and bool(b.get("email", "").strip())
        if is_valid:
            valid_buyers.append(b)
        else:
            invalid_buyers.append(b)
            
    valid_buyers.sort(key=lambda b: b.get("discovered_date", ""), reverse=True)
    invalid_buyers.sort(key=lambda b: b.get("discovered_date", ""), reverse=True)
    
    return valid_buyers + invalid_buyers

@app.route('/buyers')
def buyers():
    """View & Manage Discovered Buyers"""
    buyer_list = read_buyers_csv()
    sent_emails = load_sent_log_emails()
    
    # Mark which buyers have already been emailed
    for b in buyer_list:
        em = b.get("email", "").lower()
        b["already_sent"] = em in sent_emails if em else False
        
    # Apply priority sorting (Valid buyers first, newest discovered first)
    sorted_buyers = sort_buyers_by_priority(buyer_list)
        
    return render_template('buyers.html', buyers=sorted_buyers)


@app.route('/classify', methods=['POST'])
def classify():
    """Trigger Gemini AI Classification for Buyers"""
    buyer_list = read_buyers_csv()
    classified_count = 0
    
    for b in buyer_list:
        if b.get("classification") in ["Unclassified", "", None]:
            category = classify_contact(
                company_name=b.get("company_name", ""),
                buyer_name=b.get("buyer_name", ""),
                website=b.get("website", ""),
                category=b.get("business_category", "")
            )
            b["classification"] = category
            classified_count += 1
            
    write_buyers_csv(buyer_list)
    flash(f"Gemini AI successfully classified {classified_count} contacts!", "success")
    return redirect(url_for('buyers'))

@app.route('/send_outreach', methods=['POST'])
def send_outreach():
    """Send Gmail Outreach to Selected Buyers"""
    selected_emails = request.form.getlist('selected_emails')
    custom_subject = request.form.get('subject', 'Wholesale Himalayan Singing Bowls – OM Enterprise')
    custom_body = request.form.get('body', '')
    
    if not selected_emails:
        flash("Please select at least one buyer email to send outreach.", "warning")
        return redirect(url_for('buyers'))
        
    # Check assets
    poster_img_path = os.path.join(config.BASE_DIR, 'assets', 'product_poster.jpg')
    pptx_path = os.path.join(config.BASE_DIR, 'assets', 'singing_bowl_product.pdf')
    
    if not os.path.exists(pptx_path):
        pptx_path = config.get_attachment_path()
        
    buyer_list = read_buyers_csv()
    buyers_dict = {b.get("email"): b for b in buyer_list if b.get("email")}
    
    sent_count = 0
    failed_count = 0
    skipped_count = 0
    sheets_updated_count = 0
    sheets_failed_count = 0
    
    for email in selected_emails:
        # Do not send email if recipient email is invalid or blank
        is_valid, _ = validate_email(email)
        if not is_valid or not email.strip():
            failed_count += 1
            continue

        buyer_data = buyers_dict.get(email, {})
        company_name = buyer_data.get("company_name", "Import Partner")
        buyer_name = buyer_data.get("buyer_name", "") or company_name
        country = buyer_data.get("country", "your market")
        
        # Use custom body if provided, else use exact default template
        template_to_use = custom_body if custom_body else DEFAULT_EMAIL_TEMPLATE
        
        # Substitute all dynamic placeholders with sender & buyer info
        body_text = template_to_use.replace("{{name}}", buyer_name)
        body_text = body_text.replace("{{company}}", company_name)
        body_text = body_text.replace("{{country}}", country)
        body_text = body_text.replace("{{sender_name}}", "Yash Manglani")
        body_text = body_text.replace("{{company_name}}", "OM Enterprise")
        body_text = body_text.replace("{{email}}", config.GMAIL_EMAIL if config.GMAIL_EMAIL else "exportindia2026us@gmail.com")
        body_text = body_text.replace("{{phone}}", "+91 80577 10065")
        body_text = body_text.replace("{{website}}", "www.omenterprise.com")

        success, msg = send_email(
            email, 
            company_name, 
            custom_subject, 
            body_text, 
            attachment_path=pptx_path,
            poster_image_path=poster_img_path,
            buyer_website=buyer_data.get("website", ""),
        )
        if success:
            sent_count += 1
            if "Sheet: Updated" in msg:
                sheets_updated_count += 1
            elif "Sheet: Failed" in msg:
                sheets_failed_count += 1
        elif "Skipped" in msg:
            skipped_count += 1
        else:
            failed_count += 1
            
    # Build sheet status summary
    if sheets_updated_count > 0 and sheets_failed_count == 0:
        sheet_status = f" | ✅ Google Sheet: {sheets_updated_count} row(s) updated."
    elif sheets_updated_count > 0 and sheets_failed_count > 0:
        sheet_status = f" | ⚠️ Google Sheet: {sheets_updated_count} updated, {sheets_failed_count} failed (check logs)."
    elif sent_count > 0 and sheets_failed_count > 0:
        sheet_status = f" | ❌ Google Sheet: All {sheets_failed_count} update(s) failed — check credentials/logs."
    else:
        sheet_status = ""

    flash(
        f"Outreach Complete: {sent_count} Sent with inline poster & PPT attached | "
        f"{skipped_count} Skipped | {failed_count} Failed.{sheet_status}",
        "info"
    )
    return redirect(url_for('report'))


@app.route('/sync_sheet', methods=['POST'])
def sync_sheet():
    """
    AJAX endpoint — Full sync of ALL successfully SENT outreach emails
    from sent_log.csv to the 'Yash Manglani' Google Sheet tab.
    Returns JSON so the browser button can show progress without page reload.
    """
    # --- Build website lookup from buyers.csv ---
    website_map = {}
    if os.path.exists(config.BUYERS_CSV_PATH):
        try:
            with open(config.BUYERS_CSV_PATH, 'r', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    em = row.get('email', '').strip().lower()
                    web = row.get('website', '').strip()
                    if em and web:
                        website_map[em] = web
        except Exception as e:
            print(f"[App] /sync_sheet: could not read buyers.csv for websites: {e}")

    # --- Load unique SENT records from sent_log.csv ---
    sent_records = []
    seen = set()

    if not os.path.exists(config.SENT_LOG_CSV_PATH):
        return jsonify({
            "success": False,
            "message": "sent_log.csv not found — no sent emails to sync.",
            "synced": 0, "failed": 0, "skipped": 0,
        }), 200

    try:
        with open(config.SENT_LOG_CSV_PATH, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                status = row.get('status', '').strip().lower()
                email  = row.get('email', '').strip()
                if status == 'sent' and email and email.lower() not in seen:
                    seen.add(email.lower())
                    sent_records.append({
                        'email':        email,
                        'company_name': row.get('company_name', '').strip(),
                        'website':      website_map.get(email.lower(), ''),
                        'discovered_date': (
                            row.get('sent_date', '').strip()
                            or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        ),
                        'validation_status': 'Sent',
                    })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error reading sent_log.csv: {e}",
            "synced": 0, "failed": 0, "skipped": 0,
        }), 200

    if not sent_records:
        return jsonify({
            "success": False,
            "message": "No successfully sent emails found in sent_log.csv.",
            "synced": 0, "failed": 0, "skipped": 0,
        }), 200

    print(f"[App] /sync_sheet triggered — syncing {len(sent_records)} sent email(s) to Google Sheet...")
    sync_result = bulk_sync_to_sheets(sent_records)
    print(f"[App] /sync_sheet result: {sync_result['message']}")

    if sync_result.get('errors'):
        for err in sync_result['errors']:
            print(f"[App] /sync_sheet error detail: {err}")

    status_code = 200 if sync_result.get('success') else 207
    return jsonify({
        "success":  sync_result.get('success', False),
        "message":  sync_result.get('message', 'Unknown result'),
        "synced":   sync_result.get('synced', 0),
        "failed":   sync_result.get('failed', 0),
        "skipped":  sync_result.get('skipped', 0),
        "errors":   sync_result.get('errors', []),
    }), status_code



@app.route('/today_sent')
def today_sent():
    """
    Lightweight JSON endpoint — returns today's sent email count from sent_log.csv.
    Called by the report page JS to auto-update the counter after an outreach send.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    count = 0
    total_sent = 0
    failed = 0

    if os.path.exists(config.SENT_LOG_CSV_PATH):
        try:
            with open(config.SENT_LOG_CSV_PATH, 'r', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    st = row.get("status", "").strip().lower()
                    if st == "sent":
                        total_sent += 1
                        if row.get("sent_date", "").strip().startswith(today_str):
                            count += 1
                    elif st == "failed":
                        failed += 1
        except Exception as e:
            print(f"[App] /today_sent: error reading sent_log.csv: {e}")

    attempted = total_sent + failed
    rate = round(total_sent / attempted * 100, 1) if attempted > 0 else 0.0

    return jsonify({
        "today_sent": count,
        "total_sent": total_sent,
        "failed": failed,
        "success_rate": rate,
        "today_str": today_str,
    })


@app.route('/report')
def report():
    """Analytics & Campaign Report Dashboard"""
    buyers = read_buyers_csv()
    
    total_buyers = len(buyers)
    valid_emails = sum(1 for b in buyers if b.get("validation_status") == "Valid Format")
    invalid_emails = sum(1 for b in buyers if b.get("validation_status") == "Invalid Format")
    
    business_contacts = sum(1 for b in buyers if b.get("classification") == "Business")
    individual_contacts = sum(1 for b in buyers if b.get("classification") == "Individual")
    
    # Today's date in local time (YYYY-MM-DD) — used to filter today's sent emails
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Read sent_log.csv metrics
    sent_logs = []
    sent_count = 0
    today_sent_count = 0
    failed_count = 0
    skipped_count = 0
    
    if os.path.exists(config.SENT_LOG_CSV_PATH):
        try:
            with open(config.SENT_LOG_CSV_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sent_logs.append(dict(row))
                    st = row.get("status", "").lower()
                    if st == "sent":
                        sent_count += 1
                        # Count today's sent emails by comparing date prefix of sent_date
                        sent_date_raw = row.get("sent_date", "").strip()
                        if sent_date_raw.startswith(today_str):
                            today_sent_count += 1
                    elif st == "failed":
                        failed_count += 1
                    elif st == "skipped":
                        skipped_count += 1
        except Exception as e:
            print(f"[App] Error reading sent_log.csv: {e}")
            
    # Success rate = sent / (sent + failed) * 100, guarded against division-by-zero
    attempted = sent_count + failed_count
    success_rate = round((sent_count / attempted * 100), 1) if attempted > 0 else 0.0

    metrics = {
        "total_buyers": total_buyers,
        "valid_emails": valid_emails,
        "invalid_emails": invalid_emails,
        "business_contacts": business_contacts,
        "individual_contacts": individual_contacts,
        "sent_count": sent_count,
        "today_sent_count": today_sent_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "success_rate": success_rate,
        "today_str": today_str,
    }
    
    return render_template('report.html', metrics=metrics, sent_logs=sent_logs)

if __name__ == '__main__':
    print("Starting API EXPORT Application on http://127.0.0.1:5000...")
    app.run(debug=True, port=5000)
