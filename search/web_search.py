import requests
import re
from urllib.parse import urlparse
import config

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}\b'
PHONE_REGEX = r'(\+?\d{1,4}[-.\s]?)?(\(?\d{2,5}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,5}'

def extract_phone(text):
    """Utility to extract potential business phone numbers from text snippets."""
    if not text:
        return ""
    matches = re.findall(PHONE_REGEX, text)
    if matches:
        raw_phone = "".join(matches[0]).strip()
        if len(re.sub(r'\D', '', raw_phone)) >= 7:
            return raw_phone
    return ""

def google_search_buyers(keyword, country, limit=10):
    """
    Finds real buyer leads using Google Custom Search API or web search fallback.
    Returns list of normalized buyer dictionaries with source_platform = 'Google'.
    """
    results = []
    query = f"{keyword} {country} email OR contact"
    
    if getattr(config, 'GOOGLE_API_KEY', None) and getattr(config, 'GOOGLE_SEARCH_ENGINE_ID', None):
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": config.GOOGLE_API_KEY,
                "cx": config.GOOGLE_SEARCH_ENGINE_ID,
                "q": query,
                "num": min(limit, 10)
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", []):
                    title = item.get("title", "")
                    link = item.get("link", "")
                    snippet = item.get("snippet", "")
                    
                    company = title.split("-")[0].split("|")[0].split(":")[0].strip()
                    if not company:
                        company = urlparse(link).netloc.replace("www.", "").capitalize()
                        
                    email_match = re.search(EMAIL_REGEX, snippet)
                    found_email = email_match.group(0).lower() if email_match else ""
                    found_phone = extract_phone(snippet)
                    
                    results.append({
                        "buyer_name": company,
                        "company_name": company,
                        "email": found_email,
                        "phone": found_phone,
                        "website": link,
                        "country": country,
                        "business_category": f"{keyword.capitalize()} Buyer",
                        "source_platform": "Google"
                    })
                    if len(results) >= limit:
                        break
                if results:
                    return results
        except Exception as e:
            print(f"[GoogleSearch] Google Custom Search API call failed: {e}")

    return results

search_buyers = google_search_buyers
