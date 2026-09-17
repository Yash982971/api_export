import requests
import re
from urllib.parse import urlparse
import config

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
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

def linkedin_search_buyers(keyword, country, limit=5):
    """
    Finds real buyer profiles & company pages on LinkedIn using:
    1. Official LinkedIn API (if LINKEDIN_API_KEY is configured & authorized)
    2. Tavily Search API targeting site:linkedin.com
    3. Public web search fallback
    Returns list of normalized buyer dictionaries with source_platform = 'LinkedIn'.
    """
    results = []
    query = f"site:linkedin.com/company OR site:linkedin.com/in {keyword} importer OR distributor {country} email OR contact"
    
    # 1. Official LinkedIn API (Company Search Endpoint)
    if config.LINKEDIN_API_KEY:
        try:
            url = "https://api.linkedin.com/v2/companySearch"
            headers = {"Authorization": f"Bearer {config.LINKEDIN_API_KEY}"}
            params = {"q": f"{keyword} {country}", "count": limit}
            res = requests.get(url, headers=headers, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for comp in data.get("elements", []):
                    name = comp.get("vanityName", comp.get("name", "LinkedIn Business"))
                    link = f"https://www.linkedin.com/company/{name}"
                    
                    results.append({
                        "buyer_name": name,
                        "company_name": name,
                        "email": "",
                        "phone": "",
                        "website": link,
                        "country": country,
                        "business_category": f"{keyword.capitalize()} Importer (LinkedIn)",
                        "source_platform": "LinkedIn"
                    })
                    if len(results) >= limit:
                        break
                if results:
                    return results
            else:
                print(f"[LinkedInSearch] LinkedIn API Notice ({res.status_code}): Credentials/Permissions limited ({res.text[:100]}). Falling back to search index...")
        except Exception as e:
            print(f"[LinkedInSearch] LinkedIn API call error: {e}")

    # 2. Tavily Search API targeting LinkedIn
    if config.TAVILY_API_KEY:
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": config.TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": limit
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("results", []):
                    title = item.get("title", "")
                    link = item.get("url", "")
                    snippet = item.get("content", "")
                    
                    if "linkedin.com" in link:
                        name = title.replace("- LinkedIn", "").replace("| LinkedIn", "").strip()
                        if not name:
                            name = "LinkedIn Lead"
                            
                        email_match = re.search(EMAIL_REGEX, snippet)
                        found_email = email_match.group(0).lower() if email_match else ""
                        found_phone = extract_phone(snippet)
                        
                        results.append({
                            "buyer_name": name,
                            "company_name": name,
                            "email": found_email,
                            "phone": found_phone,
                            "website": link,
                            "country": country,
                            "business_category": f"{keyword.capitalize()} Importer (LinkedIn)",
                            "source_platform": "LinkedIn"
                        })
                    if len(results) >= limit:
                        break
                if results:
                    return results
            else:
                print(f"[LinkedInSearch] Tavily API Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[LinkedInSearch] Tavily Search API failed: {e}")

    # 3. Public Web Search Fallback
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        ddg_url = "https://html.duckduckgo.com/html/"
        res = requests.post(ddg_url, data={"q": query}, headers=headers, timeout=10)
        
        if res.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, "html.parser")
            titles = soup.find_all("a", class_="result__a")
            snippets = soup.find_all("a", class_="result__snippet")
            
            for i, t in enumerate(titles):
                link = t.get("href", "")
                title_text = t.get_text().strip()
                snippet_text = snippets[i].get_text().strip() if i < len(snippets) else ""
                
                if "linkedin.com" in link:
                    name = title_text.replace("- LinkedIn", "").replace("| LinkedIn", "").strip()
                    
                    email_match = re.search(EMAIL_REGEX, snippet_text)
                    found_email = email_match.group(0).lower() if email_match else ""
                    found_phone = extract_phone(snippet_text)
                    
                    results.append({
                        "buyer_name": name,
                        "company_name": name,
                        "email": found_email,
                        "phone": found_phone,
                        "website": link,
                        "country": country,
                        "business_category": f"{keyword.capitalize()} Buyer (LinkedIn)",
                        "source_platform": "LinkedIn"
                    })
                if len(results) >= limit:
                    break
    except Exception as e:
        print(f"[LinkedInSearch] Fallback search error: {e}")
        
    return results

# Alias for backward compatibility
search_linkedin_buyers = linkedin_search_buyers
