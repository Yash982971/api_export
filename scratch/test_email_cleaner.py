import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from search.discovery_engine import clean_extracted_email

def test_cleaner():
    samples = [
        ("besthimalayaglobal@gmail.com", "besthimalayaglobal@gmail.com"),
        ("info@bodhisattva.com", "info@bodhisattva.com"),
        ("%20sales@mefree.com", "sales@mefree.com"),
        ("info@rawsomeshack.comcall", "info@rawsomeshack.com"),
        ("hello@silentmindbowls.com", "hello@silentmindbowls.com"),
        ("support@smokeaxis.com", "support@smokeaxis.com"),
    ]
    
    print("Testing clean_extracted_email():")
    for input_email, expected in samples:
        output = clean_extracted_email(input_email)
        status = "PASSED" if output == expected else f"FAILED (got {output})"
        print(f"  {input_email} -> {output} [{status}]")
        assert output == expected

if __name__ == "__main__":
    test_cleaner()
