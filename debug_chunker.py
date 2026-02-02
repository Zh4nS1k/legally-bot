
import requests
import urllib3
import re
import trafilatura

urllib3.disable_warnings()

url = "https://adilet.zan.kz/rus/docs/K950001000_"

print(f"Fetching {url}...")
try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    resp = requests.get(url, headers=headers, verify=False, timeout=30)
    resp.encoding = resp.apparent_encoding
    text = trafilatura.extract(resp.text, include_comments=False, include_tables=False, no_fallback=True)
    
    print(f"Extracted {len(text)} chars.")
    print("--- First 500 chars ---")
    print(text[:500])
    print("--- Check for 'Статья' patterns ---")
    
    # Check what the actual headers look like
    matches = re.finditer(r"(Статья|Article)\s*(\d+)", text)
    count = 0
    for m in matches:
        print(f"Match {count}: '{text[m.start():m.end()+5]}...'") # Print match + next 5 chars
        count += 1
        if count > 10:
            break
            
    if count == 0:
        print("NO REGEX MATCHES FOUND with simple pattern!")
        
except Exception as e:
    print(e)
