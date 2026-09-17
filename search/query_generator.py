import re

# Exact 20 Singing Bowls Specific Keywords requested by user
SINGING_BOWL_KEYWORDS = [
    "singing bowls wholesaler",
    "singing bowls distributor",
    "singing bowls importer",
    "singing bowls buyer",
    "singing bowls wholesale",
    "singing bowl wholesale buyer",
    "Tibetan singing bowls wholesaler",
    "Tibetan singing bowls distributor",
    "Tibetan singing bowls importer",
    "Tibetan singing bowls buyer",
    "Himalayan singing bowls wholesaler",
    "Himalayan singing bowls distributor",
    "Himalayan singing bowls importer",
    "Himalayan singing bowls buyer",
    "singing bowl retailer",
    "singing bowl shop",
    "singing bowl store",
    "singing bowls wholesale supplier",
    "singing bowls wholesale company",
    "singing bowls bulk buyer"
]

def _build_location_string(country, state=""):
    """Combines state and country into a clean location string for search queries."""
    c_clean = country.strip() if country else "USA"
    s_clean = state.strip() if state else ""
    
    if s_clean and s_clean.lower() not in c_clean.lower():
        return f"{s_clean} {c_clean}"
    return c_clean

def get_initial_query_batch(product, country, state=""):
    """
    Returns the primary Singing Bowl specific buyer queries using state and country.
    """
    loc_target = _build_location_string(country, state)
    p_clean = product.strip() if product else "Singing Bowls"
    p_lower = p_clean.lower()
    
    if "singing bowl" in p_lower or "bowl" in p_lower or "singing" in p_lower or not product:
        return [f"{kw} {loc_target}" for kw in SINGING_BOWL_KEYWORDS[:6]]
        
    p_singular = p_clean[:-1] if p_lower.endswith('s') else p_clean
    return [
        f"{p_singular} wholesaler {loc_target}",
        f"{p_singular} distributor {loc_target}",
        f"{p_singular} importer {loc_target}",
        f"{p_singular} buyer {loc_target}",
        f"{p_singular} wholesale supplier {loc_target}",
        f"{p_singular} store {loc_target}"
    ]

def get_fallback_query_batch(product, country, state=""):
    """
    Returns secondary queries (7-20) using state and country.
    """
    loc_target = _build_location_string(country, state)
    p_clean = product.strip() if product else "Singing Bowls"
    p_lower = p_clean.lower()
    
    if "singing bowl" in p_lower or "bowl" in p_lower or "singing" in p_lower or not product:
        return [f"{kw} {loc_target}" for kw in SINGING_BOWL_KEYWORDS[6:]]
        
    p_singular = p_clean[:-1] if p_lower.endswith('s') else p_clean
    return [
        f"{p_singular} wholesale buyer {loc_target}",
        f"{p_singular} wholesale company {loc_target}",
        f"{p_singular} bulk buyer {loc_target}",
        f"{p_singular} shop {loc_target}",
        f"{p_singular} retailer {loc_target}"
    ]

def generate_buyer_queries(product, country, state=""):
    """Returns all 20 Singing Bowl specific queries appended with state and country."""
    return get_initial_query_batch(product, country, state) + get_fallback_query_batch(product, country, state)
