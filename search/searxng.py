import requests
import re
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup
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

def _parse_ddg_url(raw_href):
    """Extract clean target URL from DuckDuckGo redirect link."""
    if "uddg=" in raw_href:
        try:
            param = raw_href.split("uddg=")[1].split("&")[0]
            return unquote(param)
        except Exception:
            pass
    if raw_href.startswith("//"):
        return "https:" + raw_href
    return raw_href

def searxng_search_buyers(keyword, country, limit=10):
    """
    Finds B2B buyer leads using local SearXNG meta-search engine (http://localhost:8080).
    Includes automatic web search fallback if local SearXNG engine is offline.
    Returns list of normalized buyer dictionaries with source_platform = 'SearXNG'.
    """
    results = []
    searxng_base = config.SEARXNG_URL.rstrip('/')
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 1. Attempt SearXNG Search (Local Instance http://localhost:8080)
    try:
        url = f"{searxng_base}/search"
        params = {"q": keyword}
        res = requests.get(url, headers=headers, params=params, timeout=5)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            articles = soup.find_all("article", class_="result")
            
            for art in articles:
                title_elem = art.find("h3") or art.find("a")
                title = title_elem.get_text().strip() if title_elem else ""
                
                link_elem = art.find("a", href=True)
                link = link_elem["href"].strip() if link_elem else ""
                
                content_elem = art.find("p", class_="content") or art.find("div", class_="content")
                snippet = content_elem.get_text().strip() if content_elem else art.get_text()
                
                if not link or not link.startswith("http") or "localhost" in link:
                    continue
                    
                company = title.split("-")[0].split("|")[0].split(":")[0].strip()
                if not company or len(company) < 2:
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
                    "source_platform": "SearXNG"
                })
                if len(results) >= limit:
                    break
            if results:
                return results
    except Exception as e:
        print(f"[SearXNG] Local SearXNG engine check on {searxng_base}: {e}")

    # 2. Web Search Fallback (Direct Meta-Search HTML parser)
    try:
        ddg_url = "https://html.duckduckgo.com/html/"
        params = {"q": f"{keyword} contact"}
        res = requests.get(ddg_url, headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            articles = soup.find_all("div", class_=lambda c: c and "web-result" in c)
            
            for art in articles:
                title_elem = art.find("a", class_="result__a")
                title = title_elem.get_text().strip() if title_elem else ""
                
                raw_href = title_elem["href"].strip() if (title_elem and title_elem.has_attr("href")) else ""
                link = _parse_ddg_url(raw_href)
                
                snippet_elem = art.find("a", class_="result__snippet")
                snippet = snippet_elem.get_text().strip() if snippet_elem else ""
                
                if not link or not link.startswith("http") or "duckduckgo.com" in link:
                    continue
                    
                company = title.split("-")[0].split("|")[0].split(":")[0].strip()
                if not company or len(company) < 2:
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
                    "source_platform": "SearXNG"
                })
                if len(results) >= limit:
                    break
            return results
    except Exception as e:
        print(f"[SearXNG] Web search fallback failed: {e}")

    return results

search_searxng_buyers = searxng_search_buyers
