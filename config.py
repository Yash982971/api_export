import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data storage paths
BUYERS_CSV_PATH = os.path.join(BASE_DIR, 'data', 'buyers.csv')
SENT_LOG_CSV_PATH = os.path.join(BASE_DIR, 'data', 'sent_log.csv')

def get_attachment_path():
    """
    Finds the product attachment file in assets directory.
    Priority: singing_bowl_product.pdf -> singing_bowl_product.pptx
    Returns path without modifying or converting the file.
    """
    assets_dir = os.path.join(BASE_DIR, 'assets')
    candidates = [
        'singing_bowl_product.pdf',
        'singing_bowl_product.pptx',
    ]
    for fname in candidates:
        p = os.path.join(assets_dir, fname)
        if os.path.exists(p):
            return p
    return os.path.join(assets_dir, 'singing_bowl_product.pdf')

ATTACHMENT_PDF_PATH = get_attachment_path()

# API Credentials & Local Services
SEARXNG_URL = os.getenv('SEARXNG_URL', 'http://localhost:8080')
VOLZA_API_KEY = os.getenv('VOLZA_API_KEY', '')
TRADEMO_API_KEY = os.getenv('TRADEMO_API_KEY', '')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
GOOGLE_SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID', os.getenv('GOOGLE_CSE_ID', ''))
FACEBOOK_API_KEY = os.getenv('FACEBOOK_API_KEY', os.getenv('FACEBOOK_ACCESS_TOKEN', ''))
LINKEDIN_API_KEY = os.getenv('LINKEDIN_API_KEY', os.getenv('LINKEDIN_ACCESS_TOKEN', ''))
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GMAIL_EMAIL = os.getenv('GMAIL_EMAIL', '')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')

# Flask configuration
SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'default_student_secret_key')

# Google Sheets API configuration (for automatic outreach tracking)
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv(
    'GOOGLE_SHEETS_SPREADSHEET_ID',
    '1TpqpbO9_cYFGDcFqIVidmvJR2lm5ply4ok-TFmP6H_I'
)
GOOGLE_SHEETS_TAB_NAME = os.getenv('GOOGLE_SHEETS_TAB_NAME', 'Yash Manglani')
GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', '')
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '')
