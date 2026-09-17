import sys
import os
import json

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from search.query_generator import get_initial_query_batch, get_fallback_query_batch
from search.discovery_engine import run_multi_query_buyer_discovery

def test_buyer_discovery():
    print("==================================================")
    print(" TESTING BUYER PIPELINE & DISCOVERY ENGINE ")
    print("==================================================")

    product = "Singing Bowls"
    country = "USA"

    # Execute Buyer Discovery
    print(f"\nExecuting search for '{product}' in '{country}'...")
    valid_buyers, diagnostics = run_multi_query_buyer_discovery(product, country, target_limit=10)

    print("\n==================================================")
    print(" DIAGNOSTIC PIPELINE COUNTS ")
    print("==================================================")
    print(f"  Queries executed: {diagnostics.get('queries_executed')}")
    print(f"  Tavily results: {diagnostics.get('tavily_results')}")
    print(f"  SearXNG results: {diagnostics.get('searxng_results')}")
    print(f"  Unique businesses: {diagnostics.get('unique_businesses_found')}")
    print(f"  Official websites: {diagnostics.get('official_websites_found')}")
    print(f"  Emails found: {diagnostics.get('emails_found')}")
    print(f"  Emails validated: {diagnostics.get('emails_validated')}")
    print(f"  Validated new buyers: {diagnostics.get('validated_new_buyers')}")
    print(f"  Already existing buyers in DB: {diagnostics.get('already_existing_buyers')}")
    print(f"  Batch duplicates removed: {diagnostics.get('duplicates_removed')}")
    print(f"  Final valid buyers returned: {diagnostics.get('final_valid_buyers')}")
    print("--------------------------------------------------")
    print(f"  Rejection reasons:")
    for k, v in diagnostics.get("rejection_reasons", {}).items():
        print(f"    - {k}: {v}")

    print("\n==================================================")
    print(f" DISCOVERED VALID NEW BUYERS LIST ({len(valid_buyers)}) ")
    print("==================================================")
    for idx, buyer in enumerate(valid_buyers, 1):
        print(f" {idx}. {buyer.get('company_name')} | Email: {buyer.get('email')} | Web: {buyer.get('website')} | Source: {buyer.get('source_platform')}")

    print("\nTEST COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    test_buyer_discovery()
