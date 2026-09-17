import config

def classify_contact(company_name="", buyer_name="", website="", category=""):
    """
    Uses Gemini API to classify a contact into 'Business' or 'Individual'.
    Includes simple keyword fallback if GEMINI_API_KEY is not set or fails.
    """
    if not config.GEMINI_API_KEY:
        return fallback_classification(company_name, buyer_name)
        
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        
        # Use gemini-1.5-flash model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Classify the following lead contact as either 'Business' or 'Individual'.
        Respond with ONLY one word: 'Business' or 'Individual'.
        
        Company: {company_name}
        Buyer Name: {buyer_name}
        Website: {website}
        Category: {category}
        """
        
        response = model.generate_content(prompt)
        result_text = response.text.strip().capitalize()
        
        if "Business" in result_text:
            return "Business"
        elif "Individual" in result_text:
            return "Individual"
        else:
            return fallback_classification(company_name, buyer_name)
            
    except Exception as e:
        print(f"[GeminiClassifier] API classification failed, using rule fallback: {e}")
        return fallback_classification(company_name, buyer_name)

def fallback_classification(company_name, buyer_name):
    """
    Simple beginner-friendly heuristic fallback when Gemini API key is missing or fails.
    """
    name_str = f"{company_name} {buyer_name}".lower()
    
    business_keywords = [
        "inc", "llc", "ltd", "corp", "co.", "company", "group", "enterprises",
        "traders", "importers", "exporters", "wholesale", "wholesalers", "store",
        "bazaar", "mart", "imports", "global", "trading", "crafts", "shop"
    ]
    
    for kw in business_keywords:
        if kw in name_str:
            return "Business"
            
    return "Individual"
