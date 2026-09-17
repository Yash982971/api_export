import re

def clean_buyer_data(buyer):
    """
    Cleans and normalizes buyer dictionary fields into standard format.
    """
    cleaned = dict(buyer)
    
    # Clean company & buyer name
    company = cleaned.get("company_name", "").strip()
    company = re.sub(r'\s+', ' ', company)
    cleaned["company_name"] = company.title() if company else "Unknown Business"
    
    buyer_name = cleaned.get("buyer_name", "").strip()
    buyer_name = re.sub(r'\s+', ' ', buyer_name)
    cleaned["buyer_name"] = buyer_name.title() if buyer_name else cleaned["company_name"]
    
    # Clean email
    email = cleaned.get("email", "").strip().lower()
    cleaned["email"] = email
    
    # Clean phone number
    phone = cleaned.get("phone", "").strip()
    phone = re.sub(r'[^\d+\-\s()]', '', phone).strip()
    cleaned["phone"] = phone
    
    # Clean website URL
    website = cleaned.get("website", "").strip()
    if website and not website.startswith("http"):
        website = "http://" + website
    cleaned["website"] = website
    
    # Clean country and business category
    cleaned["country"] = cleaned.get("country", "").strip().title()
    cleaned["business_category"] = cleaned.get("business_category", "").strip().title()
    
    # Clean source platform (Tavily, SearXNG, Volza, Trademo, Google, Facebook, LinkedIn)
    source = cleaned.get("source_platform", "Tavily").strip()
    if "SearXNG" in source or "Searxng" in source:
        cleaned["source_platform"] = "SearXNG"
    elif "Volza" in source:
        cleaned["source_platform"] = "Volza"
    elif "Trademo" in source:
        cleaned["source_platform"] = "Trademo"
    elif "Facebook" in source:
        cleaned["source_platform"] = "Facebook"
    elif "LinkedIn" in source or "Linkedin" in source:
        cleaned["source_platform"] = "LinkedIn"
    elif "Google" in source:
        cleaned["source_platform"] = "Google"
    else:
        cleaned["source_platform"] = "Tavily"
        
    return cleaned
