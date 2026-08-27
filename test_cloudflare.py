from curl_cffi import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_bypass():
    print("Testing connection to https://rlt.website/ using curl_cffi...")
    
    # If you have a proxy, add it to your .env file like this:
    # PROXY_URL=http://username:password@ip:port
    proxy_url = os.getenv("PROXY_URL")
    
    proxies = None
    if proxy_url:
        print(f"Using proxy: {proxy_url}")
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
    else:
        print("No PROXY_URL found in .env. Testing with your raw local IP address...")

    try:
        # We impersonate a real Chrome browser to bypass Cloudflare's TLS fingerprinting
        response = requests.get(
            "https://rlt.website/",
            proxies=proxies,
            impersonate="chrome",
            timeout=15,
            verify=False
        )
        
        print("\n" + "="*50)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("[SUCCESS] Cloudflare was bypassed.")
            print("\nFirst 500 characters of the website HTML:")
            print("-" * 50)
            print(response.text[:500])
        else:
            print(f"[FAILED] The server responded with a {response.status_code} error.")
            
    except Exception as e:
        print(f"\n[ERROR] connecting: {e}")

if __name__ == "__main__":
    test_bypass()
