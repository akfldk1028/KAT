import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sites = [
    ("Police", "https://www.police.go.kr/www/security/cyber/cyber04.jsp"),
    ("CounterScam", "https://www.counterscam112.go.kr/phishing/searchPhone.do"),
    ("BankFed", "https://portal.kfb.or.kr/voice/bankphonenumber.php"),
    ("KISA", "https://www.boho.or.kr/kr/subPage.do?menuNo=205116")
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

for name, url in sites:
    print(f"--- Analyzing {name} ---")
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        forms = soup.find_all('form')
        for i, form in enumerate(forms):
            print(f"Form {i+1}: action={form.get('action')}, method={form.get('method')}")
            inputs = form.find_all(['input', 'select'])
            for inp in inputs:
                print(f"  - {inp.name} name={inp.get('name')} id={inp.get('id')} type={inp.get('type')}")
    except Exception as e:
        print(f"Error: {e}")
    print("\n")
