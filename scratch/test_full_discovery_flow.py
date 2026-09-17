import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from search.discovery_engine import run_multi_query_buyer_discovery

print("\n==================================================")
print("TESTING BUYER DISCOVERY PIPELINE (USA -> California)")
print("==================================================")

buyers, diag = run_multi_query_buyer_discovery("Singing Bowls", "USA", state="California", target_limit=3)

print("\n--- DIAGNOSTIC RESULTS ---")
print(f"Queries executed: {diag['queries_executed']}")
print(f"SearXNG results count: {diag['searxng_results']}")
print(f"Relevance rejected: {diag['relevance_rejected']}")
print(f"Official websites found: {diag['official_websites_found']}")
print(f"Emails found: {diag['emails_found']}")
print(f"Emails validated: {diag['emails_validated']}")
print(f"Final valid buyers returned: {diag['final_valid_buyers']}")

print("\n--- DISCOVERED BUYERS ---")
for idx, b in enumerate(buyers, 1):
    print(f"{idx}. Company: {b.get('company_name')} | Email: {b.get('email')} | Web: {b.get('website')} | Country: {b.get('country')}")

print("\n[OK] END-TO-END DISCOVERY PIPELINE TEST COMPLETE")
