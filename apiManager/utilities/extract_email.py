from urllib.parse import urlparse
import tldextract


def extract_email_domain(email: str) -> str:
    domain = email.split("@")[1]
    extracted = tldextract.extract(domain)
    print(f"🎓 Extracted domain: {extracted.domain}.{extracted.suffix}")
    return f"{extracted.domain}.{extracted.suffix}"


extract_email_domain("test@tnstate.edu")
