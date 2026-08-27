import cloudscraper

def test_bypass():
    print("Testing connection to https://rlt.website/ using cloudscraper...")
    
    scraper = cloudscraper.create_scraper()
    
    try:
        response = scraper.get("https://rlt.website/", timeout=15, verify=False)
        
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
