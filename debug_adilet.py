
import requests
import urllib3
urllib3.disable_warnings()

url = "https://adilet.zan.kz/rus/docs/K1400000233"
log_file = "debug_output.txt"

strategies = [
    {
        "name": "Mozilla (Standard)",
        "headers": {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    },
    {
        "name": "Googlebot",
        "headers": {'User-Agent': 'Googlebot/2.1 (+http://www.google.com/bot.html)'}
    },
    {
        "name": "No Headers",
        "headers": {}
    },
    {
        "name": "Full Browser Headers",
        "headers": {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
    }
]

with open(log_file, "w", encoding="utf-8") as f:
    f.write(f"Testing URL: {url}\n\n")
    
    for strategy in strategies:
        f.write(f"--- Strategy: {strategy['name']} ---\n")
        try:
            resp = requests.get(url, headers=strategy['headers'], verify=False, timeout=10, allow_redirects=True)
            f.write(f"Status: {resp.status_code}\n")
            f.write(f"Final URL: {resp.url}\n")
            if resp.status_code == 200:
                f.write(f"Success! Length: {len(resp.text)}\n")
            else:
                f.write(f"Fail. Content preview: {resp.text[:200]}\n")
        except Exception as e:
            f.write(f"Exception: {e}\n")
        f.write("\n")

print("Debug complete.")
