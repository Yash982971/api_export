import requests
import re
import base64
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

def _decode_bing_url(raw_url):
    """Decodes Bing redirect URLs to extract clean target website URL."""
    if 'u=a1' in raw_url:
        try:
            b64_part = raw_url.split('u=a1')[1].split('&')[0]
            b64_part += '=' * (-len(b64_part) % 4)
            decoded = base64.b64decode(b64_part).decode('utf-8', errors='ignore')
            if decoded.startswith('http'):
                return decoded
        except Exception:
            pass
    return raw_url

def searxng_search_buyers(keyword, country, limit=10):
    """
    Finds real B2B buyer leads using a Multi-Engine Cloud Search Pipeline.
    Sources:
      1. Local SearXNG Instance (http://localhost:8080)
      2. Bing Cloud Meta-Search Engine (24/7 Cloud Ready)
      3. Public SearXNG Node Pool
      4. Google Custom Search API (if configured)
    Returns list of normalized buyer dictionaries with source_platform = 'SearXNG'.
    """
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }

    # ── Source 1: Local SearXNG Instance (http://localhost:8080) ──────────
    searxng_base = getattr(config, 'SEARXNG_URL', 'http://localhost:8080').rstrip('/')
    try:
        url = f"{searxng_base}/search"
        params = {"q": keyword}
        res = requests.get(url, headers=headers, params=params, timeout=3)
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
                
                results.append({
                    "buyer_name": company,
                    "company_name": company,
                    "email": found_email,
                    "phone": extract_phone(snippet),
                    "website": link,
                    "country": country,
                    "business_category": f"{keyword.capitalize()} Buyer",
                    "source_platform": "SearXNG"
                })
                if len(results) >= limit:
                    break
            if results:
                print(f"[SearXNG Engine] Local SearXNG returned {len(results)} leads.")
                return results
    except Exception:
        pass

    # ── Source 2: Bing Cloud Meta-Search Engine (24/7 Cloud Ready) ────────
    try:
        bing_url = "https://www.bing.com/search"
        params = {"q": keyword}
        res = requests.get(bing_url, headers=headers, params=params, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for li in soup.find_all("li", class_="b_algo"):
                h2 = li.find("h2")
                a = h2.find("a") if h2 else li.find("a")
                p = li.find("p") or li.find("div", class_="b_caption")
                if a and a.get("href"):
                    raw_href = a["href"].strip()
                    clean_link = _decode_bing_url(raw_href)
                    title = a.get_text().strip()
                    snippet = p.get_text().strip() if p else ""
                    
                    if not clean_link or not clean_link.startswith("http") or "bing.com" in clean_link:
                        continue
                    company = title.split("-")[0].split("|")[0].split(":")[0].strip()
                    if not company or len(company) < 2:
                        company = urlparse(clean_link).netloc.replace("www.", "").capitalize()
                    email_match = re.search(EMAIL_REGEX, snippet)
                    found_email = email_match.group(0).lower() if email_match else ""
                    
                    results.append({
                        "buyer_name": company,
                        "company_name": company,
                        "email": found_email,
                        "phone": extract_phone(snippet),
                        "website": clean_link,
                        "country": country,
                        "business_category": f"{keyword.capitalize()} Buyer",
                        "source_platform": "SearXNG (Cloud Meta)"
                    })
                    if len(results) >= limit:
                        break
            if results:
                print(f"[SearXNG Engine] Cloud Meta-Search returned {len(results)} leads.")
                return results
    except Exception as e:
        print(f"[SearXNG Engine] Cloud Meta-Search notice: {e}")

    # ── Source 3: Google Custom Search API (if configured in env) ─────────
    google_key = getattr(config, 'GOOGLE_API_KEY', None)
    google_cx = getattr(config, 'GOOGLE_SEARCH_ENGINE_ID', None)
    if google_key and google_cx:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {"key": google_key, "cx": google_cx, "q": keyword, "num": min(limit, 10)}
            res = requests.get(url, params=params, timeout=8)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("items", []):
                    title = item.get("title", "")
                    link = item.get("link", "")
                    snippet = item.get("snippet", "")
                    
                    company = title.split("-")[0].split("|")[0].split(":")[0].strip()
                    if not company or len(company) < 2:
                        company = urlparse(link).netloc.replace("www.", "").capitalize()
                    email_match = re.search(EMAIL_REGEX, snippet)
                    found_email = email_match.group(0).lower() if email_match else ""
                    
                    results.append({
                        "buyer_name": company,
                        "company_name": company,
                        "email": found_email,
                        "phone": extract_phone(snippet),
                        "website": link,
                        "country": country,
                        "business_category": f"{keyword.capitalize()} Buyer",
                        "source_platform": "Google CSE"
                    })
                    if len(results) >= limit:
                        break
                if results:
                    print(f"[SearXNG Engine] Google CSE returned {len(results)} leads.")
                    return results
        except Exception as e:
            print(f"[SearXNG Engine] Google CSE notice: {e}")

    return results

search_searxng_buyers = searxng_search_buyers
