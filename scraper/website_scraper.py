import requests
import re
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Suppress insecure HTTPS request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Standard email regex pattern with word boundary to prevent .comcall matches
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}\b'

# File extensions to exclude from extracted emails
INVALID_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.pdf', '.js', '.css', '.ico')

def scrape_website_emails(website_url, max_pages=6, timeout=10):
    """
    Visits public pages of a company website (/, /contact, /contact-us, /contactus, /about, /about-us, /aboutus, /wholesale, /distribution, /distributors, /footer)
    and discovers deep contact/wholesale links to extract all publicly visible business emails.
    Uses robust 10s timeout per request for thorough extraction.
    """
    found_emails = set()
    
    if not website_url:
        return []
        
    url_clean = website_url.strip()
    if not url_clean.startswith(("http://", "https://")):
        url_clean = "https://" + url_clean
        
    try:
        parsed_base = urlparse(url_clean)
        domain = parsed_base.netloc
        if not domain:
            return []
    except Exception:
        return []
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Thorough priority path list
    priority_paths = [
        "/", "/contact", "/contact-us", "/contactus", 
        "/about", "/about-us", "/aboutus", 
        "/wholesale", "/distribution", "/distributors", "/footer"
    ]
    
    pages_to_visit = [urljoin(f"https://{domain}", path) for path in priority_paths]
    visited_urls = set()
    
    for page_url in pages_to_visit:
        if page_url in visited_urls:
            continue
        visited_urls.add(page_url)
        
        if len(visited_urls) > max_pages:
            break
            
        try:
            res = requests.get(page_url, headers=headers, timeout=timeout, verify=False)
            if res.status_code == 200:
                # 1. Regex search on text content
                matches = re.findall(EMAIL_REGEX, res.text)
                for em in matches:
                    em_lower = em.lower().strip()
                    if not em_lower.endswith(INVALID_EXTENSIONS):
                        found_emails.add(em_lower)
                        
                # 2. BeautifulSoup mailto: extraction
                soup = BeautifulSoup(res.text, "html.parser")
                for mailto in soup.find_all("a", href=re.compile(r"^mailto:", re.I)):
                    raw_email = mailto.get("href").replace("mailto:", "").split("?")[0].strip()
                    if re.match(EMAIL_REGEX, raw_email):
                        em_lower = raw_email.lower()
                        if not em_lower.endswith(INVALID_EXTENSIONS):
                            found_emails.add(em_lower)
                            
                # Discover contact/wholesale links on page HTML if we haven't visited enough pages
                if len(pages_to_visit) < 12:
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag["href"].strip()
                        href_lower = href.lower()
                        if any(k in href_lower for k in ["contact", "about", "wholesale", "distribution", "dealer", "trade"]):
                            full_link = urljoin(page_url, href)
                            if urlparse(full_link).netloc == domain and full_link not in visited_urls:
                                pages_to_visit.append(full_link)
        except Exception:
            # Continue checking other priority paths if one fails or times out
            continue
            
    return list(found_emails)
