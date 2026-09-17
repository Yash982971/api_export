import sys
import os
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from worker.db import (
    init_db,
    save_buyers_to_db,
    read_all_buyers_from_db,
    record_search_history,
    get_search_history,
    get_worker_status,
    update_worker_status
)
from worker.scheduler import run_scheduled_discovery
import app as flask_app_module

def test_db_operations():
    print("\n--- TEST 1: Database Persistence & History Logging ---")
    init_db()
    
    # Save test buyer
    test_buyers = [{
        "buyer_name": "Cloud Test Buyer",
        "company_name": "Cloud Test Company",
        "email": "cloud-test-unique@example.com",
        "phone": "+1 555-0199",
        "website": "https://cloud-test-company.com",
        "country": "USA",
        "state": "California",
        "business_category": "Singing Bowls Buyer",
        "source_platform": "SearXNG",
        "validation_status": "Valid Format",
        "classification": "Wholesaler"
    }]
    
    added, updated = save_buyers_to_db(test_buyers)
    print(f"Added: {added}, Updated: {updated}")
    
    all_buyers = read_all_buyers_from_db()
    emails = [b["email"] for b in all_buyers]
    assert "cloud-test-unique@example.com" in emails, "Test buyer email should exist in SQLite database"
    print("PASS: SQLite database save and read-back working correctly.")
    
    # Record test history
    record_search_history({
        "country": "USA",
        "state": "California",
        "query_str": "singing bowls California USA",
        "total_results": 10,
        "relevant_count": 5,
        "websites_found": 5,
        "emails_found": 3,
        "valid_emails": 2,
        "duplicates_removed": 1,
        "new_buyers_added": 1,
        "rejected_count": 5
    })
    
    hist = get_search_history(limit=5)
    assert len(hist) > 0, "Search history should record entries"
    print(f"PASS: Search history recorded (latest query: '{hist[0]['query_str']}').")

def test_worker_status():
    print("\n--- TEST 2: Worker Status Tracking ---")
    update_worker_status(status="IDLE", interval_hours=6, current_state="Texas")
    st = get_worker_status()
    assert st["status"] == "IDLE", f"Expected IDLE, got {st['status']}"
    assert st["interval_hours"] == 6, f"Expected 6h interval, got {st['interval_hours']}"
    print(f"PASS: Worker status tracking working correctly (State: '{st['current_state']}').")

def test_flask_api_endpoints():
    print("\n--- TEST 3: Flask Control Panel API Endpoints ---")
    client = flask_app_module.app.test_client()
    
    # 1. /api/ping
    res_ping = client.get('/api/ping')
    assert res_ping.status_code == 200
    data_ping = json.loads(res_ping.data)
    assert data_ping["status"] == "ok"
    print("PASS: /api/ping keep-alive endpoint returned 200 OK.")
    
    # 2. /api/worker/status
    res_status = client.get('/api/worker/status')
    assert res_status.status_code == 200
    data_status = json.loads(res_status.data)
    assert "worker_status" in data_status
    print("PASS: /api/worker/status endpoint returned valid status metrics.")

if __name__ == "__main__":
    test_db_operations()
    test_worker_status()
    test_flask_api_endpoints()
    print("\n[OK] ALL CLOUD WORKER UNIT & API TESTS PASSED!")
