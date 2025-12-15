import requests
from bs4 import BeautifulSoup
import urllib3
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sites = [
    ("CounterScam", "https://www.counterscam112.go.kr/phishing/searchPhone.do"),
    ("KISA", "https://www.boho.or.kr/kr/subPage.do?menuNo=205116")
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

for name, url in sites:
    print(f"--- Analyzing {name} ---")
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        # Search for input tags using regex in case BS4 fails or structure is weird
        inputs = re.findall(r'<input[^>]*>', response.text)
        print(f"Found {len(inputs)} raw input tags.")
        for inp in inputs[:5]: # Print first 5
            print(inp)
            
        # Also look for 'name=' inside inputs
        names = re.findall(r'name=["\']([^"\']+)["\']', response.text)
        print(f"Potential names: {names[:10]}")

    except Exception as e:
        print(f"Error: {e}")
    print("\n")
