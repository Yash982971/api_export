import re

# Standard regex for simple email format validation
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Known junk/test/dummy domains
JUNK_EMAIL_DOMAINS = [
    'example.com', 'example.org', 'example.net', 'domain.com',
    'sentry.io', 'sentry.globalsources.com', 'xyz.com', 'test.com',
    'localhost', 'invalid', 'dummy.com', 'tempmail.com', 'mailinator.com'
]

# Known junk/test email prefixes, unicode escapes, & prober addresses
JUNK_EMAIL_PREFIXES = [
    'john@', 'abc@', 'your@', 'your.email@', 'eg.sample@',
    'asxvmprobertest@', 'smart.journey.prober@', 'test@', 'dummy@',
    'sample@', 'u002f', 'u003e', 'u003c', 'u0026', 'no-reply@', 'noreply@', 'user@'
]

def validate_email(email):
    """
    Validates whether an email string has a valid format and is not a junk/test address.
    Returns (is_valid: bool, status_label: str).
    """
    if not email or not isinstance(email, str):
        return False, "Missing Email"
        
    email_clean = email.strip().lower()
    
    # 1. Basic length check
    if len(email_clean) < 5 or len(email_clean) > 100:
        return False, "Invalid Length"
    
    # 2. Regex format check
    if not re.match(EMAIL_PATTERN, email_clean):
        return False, "Invalid Format"
        
    # 3. Check for known junk/dummy domain patterns
    for domain in JUNK_EMAIL_DOMAINS:
        if email_clean.endswith(domain) or f"@{domain}" in email_clean:
            return False, "Junk/Test Domain"
            
    # 4. Check for known junk email prefixes & unicode escapes
    for prefix in JUNK_EMAIL_PREFIXES:
        if email_clean.startswith(prefix):
            return False, "Junk/Test Email Prefix"
            
    # 5. Check for fake extensions mistakenly matched as emails
    if any(email_clean.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.svg', '.webp', '.js', '.css']):
        return False, "Invalid Extension Match"
        
    return True, "Valid Format"
