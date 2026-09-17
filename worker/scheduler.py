import time
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from search.discovery_engine import run_multi_query_buyer_discovery
from outreach.google_sheets_tracker import bulk_sync_to_sheets
from worker.db import (
    init_db,
    save_buyers_to_db,
    record_search_history,
    update_worker_status,
    get_worker_status
)
import config

logger = logging.getLogger(__name__)

# Target US States rotation list
TARGET_STATES = [
    "California", "Texas", "New York", "Florida", "Illinois",
    "Pennsylvania", "Ohio", "Georgia", "North Carolina", "Washington"
]
state_rotation_index = 0

scheduler = None

def run_scheduled_discovery(state_override=None, limit_override=10):
    """
    Core background buyer discovery worker task.
    Runs SearXNG discovery -> relevance filtering -> email extraction & validation -> DB save -> Google Sheets sync.
    """
    global state_rotation_index
    init_db()
    
    # 1. Pick target US State
    if state_override:
        target_state = state_override
    else:
        target_state = TARGET_STATES[state_rotation_index % len(TARGET_STATES)]
        state_rotation_index = (state_rotation_index + 1) % len(TARGET_STATES)
        
    start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[CloudWorker] Starting scheduled search for Singing Bowls in '{target_state} USA'...")
    
    update_worker_status(
        status='RUNNING_SEARCH',
        last_search_time=start_time_str,
        error_message='',
        current_state=target_state
    )
    
    try:
        # 2. Execute Discovery Engine
        discovered_buyers, diag = run_multi_query_buyer_discovery(
            keyword="Singing Bowls",
            country="USA",
            state=target_state,
            target_limit=limit_override
        )
        
        # 3. Save Discovered Buyers to Persistent DB & CSV
        new_added, updated = save_buyers_to_db(discovered_buyers)
        
        # 4. Sync Sent Log & Database to Google Sheets Tab 'Yash Manglani'
        try:
            bulk_sync_to_sheets(
                spreadsheet_id=config.GOOGLE_SHEETS_SPREADSHEET_ID,
                tab_name=config.GOOGLE_SHEETS_TAB_NAME
            )
            logger.info("[CloudWorker] Google Sheets auto-sync complete.")
        except Exception as e:
            logger.warning(f"[CloudWorker] Google Sheets sync notice: {e}")
            
        # 5. Record Detailed Search History
        history_record = {
            "country": "USA",
            "state": target_state,
            "query_str": f"Singing Bowls {target_state} USA",
            "total_results": diag.get("searxng_results", 0),
            "relevant_count": diag.get("official_websites_found", 0),
            "websites_found": diag.get("official_websites_found", 0),
            "emails_found": diag.get("emails_found", 0),
            "valid_emails": diag.get("emails_validated", 0),
            "duplicates_removed": diag.get("duplicates_removed", 0) + diag.get("already_existing_buyers", 0),
            "new_buyers_added": new_added,
            "rejected_count": diag.get("relevance_rejected", 0) + diag.get("invalid_test_emails_removed", 0)
        }
        record_search_history(history_record)
        
        # 6. Calculate Next Search Time
        status_info = get_worker_status()
        interval = status_info.get("interval_hours", 6)
        next_run_dt = datetime.now() + timedelta(hours=interval)
        next_run_str = next_run_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        update_worker_status(
            status='IDLE',
            last_search_time=start_time_str,
            next_search_time=next_run_str,
            last_buyers_added=new_added,
            error_message='',
            current_state=target_state
        )
        logger.info(f"[CloudWorker] Search completed! Added {new_added} new buyers. Next scheduled run at {next_run_str}")
        return new_added, diag
        
    except Exception as e:
        err_msg = f"Worker Error: {type(e).__name__} - {str(e)}"
        logger.error(f"[CloudWorker] Exception during discovery: {err_msg}", exc_info=True)
        update_worker_status(
            status='ERROR',
            error_message=err_msg
        )
        return 0, {}

def init_scheduler(interval_hours=6):
    """Initializes and starts the APScheduler background worker scheduler."""
    global scheduler
    init_db()
    
    if scheduler and scheduler.running:
        logger.info("[Scheduler] APScheduler is already running.")
        return scheduler

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        func=run_scheduled_discovery,
        trigger='interval',
        hours=interval_hours,
        id='scheduled_buyer_discovery',
        name='Periodic Singing Bowl Buyer Discovery',
        replace_existing=True
    )
    scheduler.start()
    
    next_run_dt = datetime.now() + timedelta(hours=interval_hours)
    next_run_str = next_run_dt.strftime("%Y-%m-%d %H:%M:%S")
    update_worker_status(
        status='IDLE',
        next_search_time=next_run_str,
        interval_hours=interval_hours
    )
    logger.info(f"[Scheduler] APScheduler initialized 24/7 background worker (interval: {interval_hours}h, next run: {next_run_str}).")
    return scheduler

def trigger_manual_discovery(state="California", limit=10):
    """Triggers an immediate background discovery run."""
    import threading
    t = threading.Thread(target=run_scheduled_discovery, kwargs={"state_override": state, "limit_override": limit})
    t.daemon = True
    t.start()
    return True

def set_search_interval(hours):
    """Updates the background discovery interval in hours."""
    global scheduler
    if not scheduler:
        scheduler = init_scheduler(interval_hours=hours)
    else:
        scheduler.reschedule_job(
            job_id='scheduled_buyer_discovery',
            trigger='interval',
            hours=hours
        )
        next_run_dt = datetime.now() + timedelta(hours=hours)
        update_worker_status(
            interval_hours=hours,
            next_search_time=next_run_dt.strftime("%Y-%m-%d %H:%M:%S")
        )
    return True
