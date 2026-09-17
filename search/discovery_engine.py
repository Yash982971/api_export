import re
import time
import logging
from urllib.parse import urlparse

from search.query_generator import generate_buyer_queries
from search.searxng import searxng_search_buyers
from search.relevance_filter import evaluate_singing_bowl_relevance
from scraper.website_scraper import scrape_website_emails
from processing.cleaner import clean_buyer_data
from processing.validator import validate_email
from processing.duplicate_checker import load_existing_emails

logger = logging.getLogger(__name__)

# List of directory aggregators, market research sites, social media, & search engines to filter out
IGNORED_DOMAINS = {
    # Search engines & social media
    "google.com", "duckduckgo.com", "bing.com", "yahoo.com",
    "facebook.com", "linkedin.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
    "wikipedia.org", "pinterest.com", "reddit.com", "tiktok.com",
    # E-commerce marketplaces & directory aggregators
    "amazon.com", "ebay.com", "walmart.com", "etsy.com", "alibaba.com", "indiamart.com",
    "tradeindia.com", "exportersindia.com", "globalsources.com", "ec21.com", "ecplaza.net",
    "made-in-china.com", "go4worldbusiness.com", "dhgate.com",
    # Directories & Data aggregators
    "yelp.com", "yellowpages.com", "tripadvisor.com", "dnb.com", "zoominfo.com",
    "apollo.io", "crunchbase.com", "bloomberg.com", "pitchbook.com",
    # Market research report websites
    "dataintelo.com", "growthmarketreports.com", "reportsanddata.com", "verifiedmarketresearch.com",
    "grandviewresearch.com", "maximizemarketresearch.com", "mintel.com", "marketresearch.com",
    "researchandmarkets.com", "alliedmarketresearch.com", "coherentmarketinsights.com"
}

def is_official_website(url):
    """Checks if a URL is likely an official company website."""
    if not url or not url.startswith("http"):
        return False
    try:
        domain = urlparse(url).netloc.replace("www.", "").lower()
        if not domain or domain in IGNORED_DOMAINS or any(domain.endswith(f".{d}") for d in IGNORED_DOMAINS):
            return False
        return True
    except Exception:
        return False

def extract_domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "").lower()
    except Exception:
        return ""

def clean_extracted_email(email_str):
    """Clean trailing text/junk & leading unicode escape sequences from extracted emails."""
    if not email_str:
        return ""
    em = email_str.strip().lower()
    # 1. Remove leading unicode escape sequences (e.g. u003e) or URL encoding or junk
    em = re.sub(r'^(?:u00[0-9a-f]{2}|%20|\s|[^\w+.-])+', '', em)
    # 2. Fix trailing word junk attached to TLD (e.g. .comcall -> .com)
    em = re.sub(r'(\.(?:com|org|net|info|biz|gov|edu|co|io|in|us))[a-z]{2,}$', r'\1', em)
    return em

def run_multi_query_buyer_discovery(keyword, country, state="", target_limit=10):
    """
    Discovery engine using SearXNG search engine with strict Singing Bowl relevance filtering.
    State parameter targets specific US states in search queries.
    """
    t_start_total = time.time()
    existing_emails = load_existing_emails()
    
    # Generate all 20 Singing Bowls specific search queries (with state + country target)
    queries = generate_buyer_queries(keyword, country, state)
    
    diagnostics = {
        "queries_executed": 0,
        "searxng_results": 0,
        "relevance_rejected": 0,
        "unique_businesses_found": 0,
        "official_websites_found": 0,
        "emails_found": 0,
        "emails_validated": 0,
        "validated_new_buyers": 0,
        "already_existing_buyers": 0,
        "invalid_test_emails_removed": 0,
        "duplicates_removed": 0,
        "final_valid_buyers": 0,
        "search_time_sec": 0.0,
        "extraction_time_sec": 0.0,
        "validation_time_sec": 0.0,
        "total_time_sec": 0.0,
        "rejection_reasons": {
            "relevance_failed": 0,
            "no_official_website": 0,
            "no_email_on_website": 0,
            "email_validation_failed": 0,
            "already_in_database": 0,
            "duplicate_email_in_batch": 0
        }
    }
    
    visited_websites = set()
    batch_valid_emails = set()
    seen_domains_count = set()
    valid_buyers = []
    
    loc_str = f"{state} {country}".strip() if state else country
    logger.info(f"[DiscoveryEngine] Starting search for '{keyword}' in '{loc_str}'. Total queries: {len(queries)}. Existing DB emails: {len(existing_emails)}")
    
    for q_idx, query_str in enumerate(queries, 1):
        if len(valid_buyers) >= target_limit:
            logger.info(f"[DiscoveryEngine] Target limit of {target_limit} new valid buyers reached after query {q_idx-1}.")
            break
            
        diagnostics["queries_executed"] += 1
        logger.info(f"[DiscoveryEngine] Executing Query #{q_idx}/{len(queries)}: '{query_str}'")
        
        t_q_start = time.time()
        
        # Call SearXNG search directly
        try:
            s_res = searxng_search_buyers(query_str, country, limit=10)
            query_leads = s_res if s_res else []
            diagnostics["searxng_results"] += len(query_leads)
        except Exception as e:
            logger.warning(f"[DiscoveryEngine] SearXNG error: {e}")
            query_leads = []
            
        diagnostics["search_time_sec"] += (time.time() - t_q_start)
        
        if not query_leads:
            continue
            
        for lead in query_leads:
            if len(valid_buyers) >= target_limit:
                break
                
            website = lead.get("website", "").strip()
            title = lead.get("buyer_name", "") or lead.get("company_name", "")
            snippet = lead.get("business_category", "") or lead.get("snippet", "")
            company_name = lead.get("company_name", "").strip()
            
            # 1. STRICT SINGING BOWL RELEVANCE CHECK
            grade, is_rel, reason = evaluate_singing_bowl_relevance(title, snippet, website)
            if not is_rel:
                diagnostics["relevance_rejected"] += 1
                diagnostics["rejection_reasons"]["relevance_failed"] += 1
                logger.info(f"[RelevanceFilter] REJECTED '{company_name}' ({website}) - Grade: {grade} | Reason: {reason}")
                continue
                
            logger.info(f"[RelevanceFilter] ACCEPTED '{company_name}' ({website}) - Grade: {grade}")

            # 2. Filter non-official aggregator/social media sites
            if not is_official_website(website):
                diagnostics["rejection_reasons"]["no_official_website"] += 1
                continue
                
            domain = extract_domain(website)
            diagnostics["official_websites_found"] += 1
            if domain and domain not in seen_domains_count:
                seen_domains_count.add(domain)
                diagnostics["unique_businesses_found"] += 1
                
            # Avoid re-crawling the exact same web URL multiple times in the same run
            if website in visited_websites:
                continue
            visited_websites.add(website)

            # 3. Extract Candidate Emails (Snippet + Contact Page Scraping)
            candidate_emails = []
            snippet_email = clean_extracted_email(lead.get("email", ""))
            if snippet_email:
                candidate_emails.append(snippet_email)
                
            t_ext_start = time.time()
            if website:
                scraped = scrape_website_emails(website, max_pages=6, timeout=10)
                for sc_em in scraped:
                    sc_clean = clean_extracted_email(sc_em)
                    if sc_clean and sc_clean not in candidate_emails:
                        candidate_emails.append(sc_clean)
            diagnostics["extraction_time_sec"] += (time.time() - t_ext_start)
            
            if not candidate_emails:
                diagnostics["rejection_reasons"]["no_email_on_website"] += 1
                continue
                
            diagnostics["emails_found"] += len(candidate_emails)
            
            # 4. Validate Discovered Emails & Detailed [BuyerPipeline] Trace
            t_val_start = time.time()
            for cand_email in candidate_emails:
                is_val, status_lbl = validate_email(cand_email)
                
                if not is_val:
                    diagnostics["invalid_test_emails_removed"] += 1
                    diagnostics["rejection_reasons"]["email_validation_failed"] += 1
                    continue
                    
                diagnostics["emails_validated"] += 1
                
                # Check email duplicate conditions
                already_in_db = cand_email in existing_emails
                duplicate_in_batch = cand_email in batch_valid_emails
                
                final_rejected = already_in_db or duplicate_in_batch
                
                if already_in_db:
                    rejection_reason = "Already exists in database"
                    diagnostics["already_existing_buyers"] += 1
                    diagnostics["rejection_reasons"]["already_in_database"] += 1
                elif duplicate_in_batch:
                    rejection_reason = "Duplicate email in batch"
                    diagnostics["duplicates_removed"] += 1
                    diagnostics["rejection_reasons"]["duplicate_email_in_batch"] += 1
                else:
                    rejection_reason = "None (Valid New Buyer)"
                    diagnostics["validated_new_buyers"] += 1
                    batch_valid_emails.add(cand_email)
                    
                    clean_lead = clean_buyer_data(lead)
                    clean_lead["email"] = cand_email
                    clean_lead["country"] = loc_str
                    clean_lead["validation_status"] = "Valid Format"
                    valid_buyers.append(clean_lead)

                # Required Detailed Log Output
                logger.info(f"[BuyerPipeline] Validated Buyer #{diagnostics['emails_validated']}:")
                logger.info(f"  Company: {company_name}")
                logger.info(f"  Email: {cand_email}")
                logger.info(f"  Website: {website}")
                logger.info(f"  Relevance grade: {grade}")
                logger.info(f"  Validation status: {status_lbl}")
                logger.info(f"  Duplicate by email: {'YES' if duplicate_in_batch else 'NO'}")
                logger.info(f"  Already in database: {'YES' if already_in_db else 'NO'}")
                logger.info(f"  Final filter rejected: {'YES' if final_rejected else 'NO'}")
                logger.info(f"  Rejection reason: {rejection_reason}")
                
                print(f"[BuyerPipeline] Validated #{diagnostics['emails_validated']} | Email: {cand_email} | Grade: {grade} | DB: {'YES' if already_in_db else 'NO'} | Added: {'YES' if not final_rejected else 'NO'}")
                
                if not final_rejected:
                    break  # Stop checking candidate emails for this company once 1 valid new buyer is added
                    
            diagnostics["validation_time_sec"] += (time.time() - t_val_start)
            
    # Final timing & buyer counts
    diagnostics["final_valid_buyers"] = len(valid_buyers)
    diagnostics["search_time_sec"] = round(diagnostics["search_time_sec"], 2)
    diagnostics["extraction_time_sec"] = round(diagnostics["extraction_time_sec"], 2)
    diagnostics["validation_time_sec"] = round(diagnostics["validation_time_sec"], 2)
    diagnostics["total_time_sec"] = round(time.time() - t_start_total, 2)
    
    logger.info(
        f"[BuyerPipeline Summary] Total Validated: {diagnostics['emails_validated']} | "
        f"New Buyers Added: {diagnostics['validated_new_buyers']} | "
        f"Already In DB: {diagnostics['already_existing_buyers']} | "
        f"Batch Duplicates: {diagnostics['duplicates_removed']}"
    )
    
    return valid_buyers, diagnostics
