import os
import csv
import sqlite3
from datetime import datetime
import config

DB_PATH = os.path.join(config.BASE_DIR, 'data', 'export_system.db')

def get_db_connection():
    """Returns a SQLite connection with row factory configured."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite database tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Buyers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buyers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_name TEXT,
            company_name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            website TEXT,
            country TEXT,
            state TEXT,
            business_category TEXT,
            source_platform TEXT,
            validation_status TEXT,
            classification TEXT DEFAULT 'Unclassified',
            discovered_date TEXT,
            updated_at TEXT
        )
    ''')
    
    # 2. Search History table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_time TEXT,
            country TEXT,
            state TEXT,
            query_str TEXT,
            total_results INTEGER DEFAULT 0,
            relevant_count INTEGER DEFAULT 0,
            websites_found INTEGER DEFAULT 0,
            emails_found INTEGER DEFAULT 0,
            valid_emails INTEGER DEFAULT 0,
            duplicates_removed INTEGER DEFAULT 0,
            new_buyers_added INTEGER DEFAULT 0,
            rejected_count INTEGER DEFAULT 0
        )
    ''')
    
    # 3. Worker Status table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS worker_status (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            status TEXT DEFAULT 'IDLE',
            last_search_time TEXT DEFAULT 'Never',
            next_search_time TEXT DEFAULT 'Pending',
            last_buyers_added INTEGER DEFAULT 0,
            total_valid_buyers INTEGER DEFAULT 0,
            error_message TEXT DEFAULT '',
            interval_hours INTEGER DEFAULT 6,
            current_state TEXT DEFAULT 'California'
        )
    ''')
    
    # Ensure default row exists in worker_status
    cursor.execute('''
        INSERT OR IGNORE INTO worker_status (id, status, last_search_time, next_search_time, last_buyers_added, total_valid_buyers, error_message, interval_hours, current_state)
        VALUES (1, 'IDLE', 'Never', 'Pending', 0, 0, '', 6, 'California')
    ''')
    
    conn.commit()

    # Initial migration: load buyers from buyers.csv into SQLite if table is empty
    cursor.execute("SELECT COUNT(*) as cnt FROM buyers")
    count = cursor.fetchone()["cnt"]
    if count == 0 and os.path.exists(config.BUYERS_CSV_PATH):
        try:
            with open(config.BUYERS_CSV_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for row in reader:
                    em = (row.get("email") or "").strip().lower()
                    if not em:
                        continue
                    cursor.execute('''
                        INSERT OR IGNORE INTO buyers (
                            buyer_name, company_name, email, phone, website,
                            country, state, business_category, source_platform,
                            validation_status, classification, discovered_date, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get("buyer_name", ""),
                        row.get("company_name", ""),
                        em,
                        row.get("phone", ""),
                        row.get("website", ""),
                        row.get("country", "USA"),
                        "California",
                        row.get("business_category", ""),
                        row.get("source_platform", "SearXNG"),
                        row.get("validation_status", "Valid Format"),
                        row.get("classification", "Unclassified"),
                        row.get("discovered_date", now_str),
                        now_str
                    ))
            conn.commit()
            print(f"[DB] Migrated existing buyers from CSV to SQLite DB.")
        except Exception as e:
            print(f"[DB] CSV Migration notice: {e}")
            
    conn.close()

def save_buyers_to_db(buyers_list):
    """
    Saves new buyers to SQLite database and updates CSV export.
    Returns (added_count, updated_count).
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    added_count = 0
    updated_count = 0
    
    for b in buyers_list:
        em = (b.get("email") or "").strip().lower()
        if not em:
            continue
            
        cursor.execute("SELECT id FROM buyers WHERE LOWER(email) = ?", (em,))
        row = cursor.fetchone()
        
        c_name = b.get("company_name", "").strip() or b.get("buyer_name", "").strip()
        b_name = b.get("buyer_name", "").strip() or c_name
        
        if row:
            # Update existing record
            cursor.execute('''
                UPDATE buyers SET
                    buyer_name = COALESCE(NULLIF(?, ''), buyer_name),
                    company_name = COALESCE(NULLIF(?, ''), company_name),
                    phone = COALESCE(NULLIF(?, ''), phone),
                    website = COALESCE(NULLIF(?, ''), website),
                    country = COALESCE(NULLIF(?, ''), country),
                    validation_status = COALESCE(NULLIF(?, ''), validation_status),
                    updated_at = ?
                WHERE id = ?
            ''', (b_name, c_name, b.get("phone", ""), b.get("website", ""), b.get("country", ""), b.get("validation_status", ""), now_str, row["id"]))
            updated_count += 1
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO buyers (
                    buyer_name, company_name, email, phone, website,
                    country, state, business_category, source_platform,
                    validation_status, classification, discovered_date, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                b_name,
                c_name,
                em,
                b.get("phone", ""),
                b.get("website", ""),
                b.get("country", "USA"),
                b.get("state", "California"),
                b.get("business_category", "Singing Bowls Buyer"),
                b.get("source_platform", "SearXNG"),
                b.get("validation_status", "Valid Format"),
                b.get("classification", "Unclassified"),
                b.get("discovered_date", now_str),
                now_str
            ))
            added_count += 1
            
    conn.commit()
    
    # Sync back to buyers.csv
    cursor.execute("SELECT * FROM buyers ORDER BY discovered_date DESC")
    all_rows = cursor.fetchall()
    conn.close()
    
    sync_buyers_to_csv([dict(r) for r in all_rows])
    return added_count, updated_count

def sync_buyers_to_csv(buyer_dicts):
    """Utility to overwrite data/buyers.csv for backwards compatibility."""
    fieldnames = [
        "buyer_name", "company_name", "email", "phone", "website", 
        "country", "business_category", "source_platform", 
        "validation_status", "classification", "discovered_date"
    ]
    try:
        os.makedirs(os.path.dirname(config.BUYERS_CSV_PATH), exist_ok=True)
        with open(config.BUYERS_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for b in buyer_dicts:
                writer.writerow(b)
    except Exception as e:
        print(f"[DB] Error syncing to buyers.csv: {e}")

def read_all_buyers_from_db():
    """Reads all buyers from SQLite database."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM buyers ORDER BY discovered_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def record_search_history(history_dict):
    """Logs a completed search execution into search_history."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO search_history (
            search_time, country, state, query_str, total_results,
            relevant_count, websites_found, emails_found, valid_emails,
            duplicates_removed, new_buyers_added, rejected_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        now_str,
        history_dict.get("country", "USA"),
        history_dict.get("state", "California"),
        history_dict.get("query_str", "Singing Bowls Search"),
        history_dict.get("total_results", 0),
        history_dict.get("relevant_count", 0),
        history_dict.get("websites_found", 0),
        history_dict.get("emails_found", 0),
        history_dict.get("valid_emails", 0),
        history_dict.get("duplicates_removed", 0),
        history_dict.get("new_buyers_added", 0),
        history_dict.get("rejected_count", 0)
    ))
    conn.commit()
    conn.close()

def get_search_history(limit=15):
    """Retrieves recent search history entries."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM search_history ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_worker_status(status=None, last_search_time=None, next_search_time=None, last_buyers_added=None, total_valid_buyers=None, error_message=None, interval_hours=None, current_state=None):
    """Updates worker_status row in SQLite."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if last_search_time is not None:
        updates.append("last_search_time = ?")
        params.append(last_search_time)
    if next_search_time is not None:
        updates.append("next_search_time = ?")
        params.append(next_search_time)
    if last_buyers_added is not None:
        updates.append("last_buyers_added = ?")
        params.append(last_buyers_added)
    if total_valid_buyers is not None:
        updates.append("total_valid_buyers = ?")
        params.append(total_valid_buyers)
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)
    if interval_hours is not None:
        updates.append("interval_hours = ?")
        params.append(interval_hours)
    if current_state is not None:
        updates.append("current_state = ?")
        params.append(current_state)
        
    if updates:
        sql = f"UPDATE worker_status SET {', '.join(updates)} WHERE id = 1"
        cursor.execute(sql, params)
        conn.commit()
        
    conn.close()

def get_worker_status():
    """Retrieves the current worker status record."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM worker_status WHERE id = 1")
    row = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) as cnt FROM buyers WHERE validation_status = 'Valid Format'")
    valid_count = cursor.fetchone()["cnt"]
    
    cursor.execute("SELECT COUNT(*) as cnt FROM buyers")
    total_count = cursor.fetchone()["cnt"]
    
    conn.close()
    
    status_dict = dict(row) if row else {
        "status": "IDLE",
        "last_search_time": "Never",
        "next_search_time": "Pending",
        "last_buyers_added": 0,
        "total_valid_buyers": valid_count,
        "error_message": "",
        "interval_hours": 6,
        "current_state": "California"
    }
    status_dict["total_valid_buyers"] = valid_count
    status_dict["total_buyers_count"] = total_count
    return status_dict
