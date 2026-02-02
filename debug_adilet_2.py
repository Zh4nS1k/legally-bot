
import requests
import urllib3
urllib3.disable_warnings()

# List of URLs to test: Home, Constitution (known good), and Problematic Code
urls_to_test = [
    ("Home", "https://adilet.zan.kz/rus"),
    ("Constitution", "https://adilet.zan.kz/rus/docs/K950001000_"),
    ("Admin Code", "https://adilet.zan.kz/rus/docs/K1400000233")
]

log_file = "debug_output_2.txt"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Upgrade-Insecure-Requests': '1'
}

with open(log_file, "w", encoding="utf-8") as f:
    for name, url in urls_to_test:
        f.write(f"--- Testing {name}: {url} ---\n")
        try:
            resp = requests.get(url, headers=headers, verify=False, timeout=10)
            f.write(f"Status: {resp.status_code}\n")
            f.write(f"Final URL: {resp.url}\n")
            f.write(f"History: {resp.history}\n")
            if resp.status_code == 200:
                f.write(f"Success! Length: {len(resp.text)}\n")
            else:
                f.write(f"Fail. Content preview: {resp.text[:200]}\n")
        except Exception as e:
            f.write(f"Exception: {e}\n")
        f.write("\n")
