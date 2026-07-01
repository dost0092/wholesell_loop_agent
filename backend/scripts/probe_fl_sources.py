"""Probe Florida county public data URLs."""
import re

import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TXFLLeadGen/0.2; research bot for public records)"
}

URLS = [
    "https://publicaccess.hillsclerk.com/TD/",
    "https://publicaccess.hillsclerk.com/api/TD/search",
    "https://www.browardcountylegalnotices.com/",
    "https://www.miamidade.gov/resources/legal-ads/",
    "https://www.miamidade.gov/clerk/property-tax-deeds.page",
]

for u in URLS:
    try:
        r = httpx.get(u, follow_redirects=True, timeout=30, headers=HEADERS)
        print(r.status_code, len(r.text), u)
        if "folio" in r.text.lower() or "tax deed" in r.text.lower():
            print("  keywords found")
    except Exception as exc:
        print("ERR", u, exc)

# Try Miami-Dade delinquent PDF
pdf_url = "https://www.miamidade.gov/resources/legal-ads/2025/2025-05-28-delinquent-real-estate-property-taxes.pdf"
try:
    r = httpx.get(pdf_url, follow_redirects=True, timeout=60, headers=HEADERS)
    print("PDF", r.status_code, len(r.content), pdf_url)
except Exception as exc:
    print("PDF ERR", exc)
