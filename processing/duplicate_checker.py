import csv
import os
import config

def load_existing_emails():
    """
    Reads all existing buyer emails from data/buyers.csv.
    """
    emails = set()
    if os.path.exists(config.BUYERS_CSV_PATH):
        try:
            with open(config.BUYERS_CSV_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    em = row.get("email", "").strip().lower()
                    if em:
                        emails.add(em)
        except Exception as e:
            print(f"[DuplicateChecker] Error reading buyers.csv: {e}")
    return emails

def load_sent_log_emails():
    """
    Reads all emails already contacted from data/sent_log.csv.
    """
    contacted = set()
    if os.path.exists(config.SENT_LOG_CSV_PATH):
        try:
            with open(config.SENT_LOG_CSV_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    em = row.get("email", "").strip().lower()
                    status = row.get("status", "").strip().lower()
                    if em and status == "sent":
                        contacted.add(em)
        except Exception as e:
            print(f"[DuplicateChecker] Error reading sent_log.csv: {e}")
    return contacted

def is_already_contacted(email):
    """
    Checks if an email has already been sent an outreach message.
    """
    if not email:
        return False
    contacted_emails = load_sent_log_emails()
    return email.strip().lower() in contacted_emails

def remove_duplicates(new_buyers):
    """
    Filters out buyers whose email already exists in buyers.csv or in the new batch.
    Returns (unique_buyers_list, duplicate_count).
    """
    existing_emails = load_existing_emails()
    seen_in_batch = set()
    unique_buyers = []
    duplicate_count = 0
    
    for buyer in new_buyers:
        email = buyer.get("email", "").strip().lower()
        company = buyer.get("company_name", "").strip().lower()
        
        key = email if email else f"company_{company}"
        
        if (email and email in existing_emails) or (key in seen_in_batch):
            duplicate_count += 1
            continue
            
        seen_in_batch.add(key)
        unique_buyers.append(buyer)
        
    return unique_buyers, duplicate_count

def merge_buyers(existing_buyers, new_buyers):
    """
    Merges newly discovered buyers with existing buyers in data/buyers.csv.
    - If a buyer is already present (by email or company_name), updates its record with new details and timestamp.
    - If a buyer is new, appends it to the list without deleting any past buyers.
    Returns (merged_list, new_added_count, updated_count).
    """
    buyers_map = {}
    order = []
    
    # 1. Load existing buyers into map maintaining original order
    for item in existing_buyers:
        em = item.get("email", "").strip().lower()
        co = item.get("company_name", "").strip().lower()
        key = em if em else f"company_{co}"
        buyers_map[key] = dict(item)
        order.append(key)
        
    new_added_count = 0
    updated_count = 0
    
    # 2. Merge new batch
    for item in new_buyers:
        em = item.get("email", "").strip().lower()
        co = item.get("company_name", "").strip().lower()
        key = em if em else f"company_{co}"
        
        if key in buyers_map:
            # Update existing record with any non-empty new values & fresh discovered_date
            existing_record = buyers_map[key]
            for k, v in item.items():
                if v:
                    existing_record[k] = v
            updated_count += 1
        else:
            buyers_map[key] = dict(item)
            order.append(key)
            new_added_count += 1
            
    merged_list = [buyers_map[k] for k in order]
    return merged_list, new_added_count, updated_count
