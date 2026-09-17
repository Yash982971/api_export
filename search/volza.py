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

def volza_search_buyers(keyword, country, limit=5):
    """
    Finds B2B trade buyers & importers using Volza data platform:
    1. Official Volza API (if VOLZA_API_KEY is configured)
    2. Tavily Search API targeting site:volza.com
    3. Public web search fallback
    Returns list of normalized buyer dictionaries with source_platform = 'Volza'.
    """
    results = []
    query = f"site:volza.com {keyword} buyer OR importer {country}"

    # 1. Official Volza API Endpoint
    if config.VOLZA_API_KEY:
        try:
            url = "https://api.volza.com/v1/buyers/search"
            headers = {"Authorization": f"Bearer {config.VOLZA_API_KEY}", "Accept": "application/json"}
            params = {"product": keyword, "country": country, "limit": limit}
            res = requests.get(url, headers=headers, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                for buyer in data.get("buyers", []):
                    name = buyer.get("company_name", buyer.get("name", "Volza Buyer"))
                    website = buyer.get("website", buyer.get("url", "https://www.volza.com"))
                    email = buyer.get("email", "")
                    phone = buyer.get("phone", "")
                    
                    results.append({
                        "buyer_name": name,
                        "company_name": name,
                        "email": email.lower(),
                        "phone": phone,
                        "website": website,
                        "country": country,
                        "business_category": f"{keyword.capitalize()} Importer (Volza)",
                        "source_platform": "Volza"
                    })
                    if len(results) >= limit:
                        break
                if results:
                    return results
            else:
                print(f"[VolzaSearch] Volza API Notice ({res.status_code}): Key/Permissions limited. Falling back to search index...")
        except Exception as e:
            print(f"[VolzaSearch] Volza API error: {e}")

    # 2. Tavily Search targeting site:volza.com
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
                    
                    name = title.replace("- Volza", "").replace("| Volza", "").replace("Buyers and Importers of", "").strip()
                    company = name.split("in")[0].split("importers")[0].strip()
                    if not company or len(company) < 3:
                        company = f"{keyword.capitalize()} Importer"
                        
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
                        "business_category": f"{keyword.capitalize()} Importer (Volza)",
                        "source_platform": "Volza"
                    })
                    if len(results) >= limit:
                        break
                if results:
                    return results
            else:
                print(f"[VolzaSearch] Tavily API Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[VolzaSearch] Tavily search failed: {e}")

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
                
                if "volza.com" in link:
                    name = title_text.replace("- Volza", "").replace("| Volza", "").strip()
                    company = name.split("in")[0].strip()
                    if not company:
                        company = f"{keyword.capitalize()} Buyer"
                        
                    email_match = re.search(EMAIL_REGEX, snippet_text)
                    found_email = email_match.group(0).lower() if email_match else ""
                    found_phone = extract_phone(snippet_text)
                    
                    results.append({
                        "buyer_name": company,
                        "company_name": company,
                        "email": found_email,
                        "phone": found_phone,
                        "website": link,
                        "country": country,
                        "business_category": f"{keyword.capitalize()} Importer (Volza)",
                        "source_platform": "Volza"
                    })
                if len(results) >= limit:
                    break
    except Exception as e:
        print(f"[VolzaSearch] Fallback search error: {e}")
        
    return results

search_volza_buyers = volza_search_buyers
