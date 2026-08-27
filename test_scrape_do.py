import requests
import urllib.parse

api_key = "b7a2fc1e11b840509bf58a1b979e7aa898b404dd24b".strip()
target_url = urllib.parse.quote("https://rlt.website/")

print("Testing Scrape.do API...")
scrape_do_url = f"http://api.scrape.do/?token={api_key}&url={target_url}"

try:
    r = requests.get(scrape_do_url, timeout=60, verify=False)
    print(f"Scrape.do Status: {r.status_code}")
    if r.status_code == 200:
        print("[SUCCESS] Scrape.do bypassed Cloudflare!")
        print("\nFirst 500 characters of the website HTML:")
        print("-" * 50)
        print(r.text[:500])
    else:
        print(f"[FAILED] Error Response: {r.text[:200]}")
except Exception as e:
    print(f"Scrape.do Error: {e}")
