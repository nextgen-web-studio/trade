import requests

api_key = "b7a2fc1e11b840509bf58a1b979e7aa898b404dd24b".strip()
url = "https://rlt.website/"

print("Testing ScrapingBee API...")
scrapingbee_url = f"https://app.scrapingbee.com/api/v1/?api_key={api_key}&url={url}&render_js=true"
try:
    r = requests.get(scrapingbee_url, timeout=60, verify=False)
    print(f"ScrapingBee Status: {r.status_code}")
    if r.status_code == 200:
        print("[SUCCESS] ScrapingBee bypassed Cloudflare!")
        print(r.text[:500])
except Exception as e:
    print(f"ScrapingBee Error: {e}")
