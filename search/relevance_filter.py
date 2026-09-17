import re
from urllib.parse import urlparse

SINGING_BOWL_TERMS = [
    "singing bowl", "singing bowls",
    "tibetan bowl", "tibetan bowls",
    "himalayan bowl", "himalayan bowls",
    "nepalese bowl", "nepalese bowls",
    "singingbowl", "singingbowls",
    "sound bowl", "sound bowls",
    "chakra bowl", "chakra bowls",
    "meditation bowl", "meditation bowls",
    "standing bowl", "standing bowls",
    "healing bowl", "healing bowls"
]

TRADE_TERMS = [
    "wholesal", "distribut", "import", "supplier", "vendor",
    "retailer", "store", "shop", "merchant", "trader", "buy", "sale",
    "product", "catalog", "order", "supply", "dealer", "b2b", "bulk"
]

REJECT_PATTERNS = [
    r"\bnews\b", r"\bblog\b", r"\barticle\b", r"\bwikipedia\b", r"\bwiki\b",
    r"\breport\b", r"\bmarket research\b", r"\bindustry trends\b",
    r"\bhow to\b", r"\bbenefits of\b", r"\bhistory of\b", r"\bguide to\b"
]

def evaluate_singing_bowl_relevance(title, snippet, website):
    """
    Strict B2B Singing Bowl Relevance Filter.
    Checks result title, snippet, and official website domain/URL.
    
    Returns:
        (grade, is_relevant, reason)
        grade: 'HIGH', 'MEDIUM', 'LOW'
        is_relevant: True if HIGH or MEDIUM, False if LOW
    """
    text_content = f"{title or ''} {snippet or ''} {website or ''}".lower()
    
    # 1. Reject news articles, blogs, market research reports, and generic guides
    for pat in REJECT_PATTERNS:
        if re.search(pat, text_content):
            return "LOW", False, f"Rejected due to content pattern: '{pat}'"
            
    # 2. Must contain explicit Singing Bowl terms
    found_sb_term = False
    for term in SINGING_BOWL_TERMS:
        if term in text_content:
            found_sb_term = True
            break
            
    if not found_sb_term:
        return "LOW", False, "No explicit Singing Bowl evidence found in title, snippet, or URL"
        
    # 3. Check for Trade / Commercial / Business evidence
    has_trade_term = any(term in text_content for term in TRADE_TERMS)
    
    # Check domain name for singing bowl or commercial keywords
    domain = ""
    try:
        domain = urlparse(website).netloc.lower()
    except Exception:
        pass

    is_sb_domain = any(term.replace(" ", "") in domain for term in ["singingbowl", "soundbowl", "tibetanbowl", "himalayanbowl"])

    if is_sb_domain or (found_sb_term and has_trade_term):
        return "HIGH", True, "Clear Singing Bowl B2B/Retail commercial evidence"
    elif found_sb_term:
        return "MEDIUM", True, "Reasonably related Singing Bowl business evidence"
        
    return "LOW", False, "Insufficient Singing Bowl business evidence"
