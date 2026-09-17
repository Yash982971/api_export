import os
import sys

# Add parent directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import config
from search.web_search import tavily_search_buyers
from search.searxng import searxng_search_buyers
from processing.cleaner import clean_buyer_data
from processing.validator import validate_email
from processing.duplicate_checker import merge_buyers

def test_tavily_searxng_pipeline(keyword="Singing Bowls", country="USA"):
    print("==================================================")
    print(f"TESTING TAVILY + SEARXNG (LOCAL 8080) PIPELINE")
    print(f"Query: Product='{keyword}', Country='{country}'")
    print("==================================================")
    
    # 1. Tavily Search API
    print("\n--- SOURCE 1: Tavily Search API ---")
    try:
        tavily_leads = tavily_search_buyers(keyword, country, limit=5)
        print(f"Tavily Search returned {len(tavily_leads)} results:")
        for idx, item in enumerate(tavily_leads, 1):
            print(f"  {idx}. [{item['source_platform']}] {item['company_name']} | Email: {item.get('email') or 'N/A'} | Site: {item.get('website')}")
    except Exception as e:
        print(f"Tavily Search Error: {e}")
        tavily_leads = []

    # 2. SearXNG Local Search (http://localhost:8080)
    print("\n--- SOURCE 2: Local SearXNG Engine (http://localhost:8080) ---")
    try:
        searxng_leads = searxng_search_buyers(keyword, country, limit=10)
        print(f"SearXNG returned {len(searxng_leads)} results:")
        for idx, item in enumerate(searxng_leads, 1):
            print(f"  {idx}. [{item['source_platform']}] {item['company_name']} | Email: {item.get('email') or 'N/A'} | Site: {item.get('website')}")
    except Exception as e:
        print(f"SearXNG Search Error: {e}")
        searxng_leads = []

    # Combined raw results
    raw_all = tavily_leads + searxng_leads
    print(f"\nTotal Raw Collected Leads across Tavily & SearXNG: {len(raw_all)}")

    # Clean & Validate
    cleaned_all = [clean_buyer_data(b) for b in raw_all]
    valid_leads = []
    junk_count = 0
    for lead in cleaned_all:
        is_valid, status = validate_email(lead.get("email", ""))
        lead["validation_status"] = status
        if is_valid and lead.get("email"):
            valid_leads.append(lead)
        else:
            junk_count += 1
            
    print(f"Leads with Valid Email (Junk/Invalid filtered: {junk_count}): {len(valid_leads)}")

    # Deduplicate against batch
    merged_batch, new_added, updated = merge_buyers([], valid_leads)
    dedup_removed = len(valid_leads) - len(merged_batch)
    
    print("\n==================================================")
    print("FINAL SUMMARY REPORT")
    print("==================================================")
    print(f"1. Tavily Search Results:  {len(tavily_leads)}")
    print(f"2. SearXNG Search Results: {len(searxng_leads)}")
    print(f"3. Total Raw Leads:        {len(raw_all)}")
    print(f"4. Duplicates Removed:     {dedup_removed}")
    print(f"5. Final Valid Leads Count: {len(merged_batch)}")
    print("==================================================")
    
    return {
        "tavily_count": len(tavily_leads),
        "searxng_count": len(searxng_leads),
        "total_raw": len(raw_all),
        "duplicates_removed": dedup_removed,
        "final_valid_count": len(merged_batch)
    }

if __name__ == "__main__":
    test_tavily_searxng_pipeline()
