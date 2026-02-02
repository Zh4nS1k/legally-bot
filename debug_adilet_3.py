
import requests
import urllib3
urllib3.disable_warnings()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Upgrade-Insecure-Requests': '1'
}

base = "https://adilet.zan.kz/rus/docs"
variants = [
    f"{base}/K1400000233",       # Original (Fail)
    f"{base}/K1400000233_",      # With underscore
    f"{base}/K1400000235",       # Guess based on Law No. 235
    f"{base}/K1400000235_",
    f"{base}/K1400000234",
    f"{base}/K1400000236",
    f"{base}/V1400000235",       # Registered Acts often start with V
    f"{base}/V1400000233"
]

log_file = "debug_output_3.txt"

with open(log_file, "w", encoding="utf-8") as f:
    for url in variants:
        f.write(f"Testing: {url}\n")
        try:
            resp = requests.get(url, headers=headers, verify=False, timeout=5)
            f.write(f"Status: {resp.status_code}\n")
            if resp.status_code == 200:
                f.write(f"SUCCESS! Found valid URL.\n")
            else:
                f.write("Fail.\n")
        except Exception as e:
            f.write(f"Error: {e}\n")
        f.write("\n")
