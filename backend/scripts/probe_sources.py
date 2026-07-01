import re
import httpx

# Dallas TRW links
r = httpx.get("https://www.dallascounty.org/departments/tax/tax-roll.php", timeout=30, follow_redirects=True)
links = re.findall(r'href=["\']([^"\']+)["\']', r.text)
print("=== Dallas TRW links ===")
for l in links:
    if any(x in l.lower() for x in ("trw", "flat", "zip", ".pdf")):
        print(l)

# Harris sale list URLs
urls = [
    "https://www.hctax.net/Property/TaxSales/ListOfSaleProperties",
    "https://www.hctax.net/Property/TaxSales/SalePropertyList",
    "https://www.hctax.net/Property/TaxSales/Properties",
    "https://www.hctax.net/Property/TaxSales/List",
    "https://www.hctax.net/Property/TaxSales/SaleProperties",
]
print("\n=== Harris URLs ===")
for u in urls:
    try:
        resp = httpx.get(u, follow_redirects=True, timeout=20)
        print(resp.status_code, len(resp.text), u)
        if resp.status_code == 200 and "table" in resp.text.lower():
            print("  has table")
    except Exception as e:
        print("ERR", u, e)
