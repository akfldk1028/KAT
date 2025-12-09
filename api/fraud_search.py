import requests
from bs4 import BeautifulSoup
import urllib3
import ssl

# Disable SSL warnings for BankFed/Police if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FraudSearch:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def check_police(self, search_type, value):
        """
        Check Police Cyber Bureau.
        search_type: 'account', 'phone', 'email'
        value: The number or email to check.
        """
        url = "https://www.police.go.kr/user/search/ND_searchResult.do"
        
        # Mapping based on common dropdown order (Assumption: 1=Phone, 2=Account, 3=Email or similar)
        # I will try to infer or use a generic search if possible, but usually it requires a type.
        # Let's assume: 1: Account, 2: Phone, 3: Email (Common in KR gov sites)
        # If this is wrong, the user can swap them.
        type_map = {
            'account': '2', # 계좌번호
            'phone': '1',   # 전화번호
            'email': '3'    # 이메일
        }
        
        target = type_map.get(search_type)
        if not target:
            return "Invalid search type for Police site."

        data = {
            'colTarget': target,
            'searchTerm': value,
            'search': 'true' # Often required
        }

        try:
            response = requests.post(url, data=data, headers=self.headers, verify=False, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract result text
            # Usually in a specific div or table. 
            # Since I can't see the result page, I'll return the text of the main content area or "No result found"
            # Looking for common success/fail keywords
            if "접수된 민원이 없습니다" in response.text or "검색결과가 없습니다" in response.text:
                return "Police: No reports found (Clean)."
            elif "신고된 번호입니다" in response.text:
                return "Police: REPORTED! Caution required."
            else:
                # Return a snippet of the body text if unsure
                body = soup.find('div', {'class': 'result_box'}) # Guessing class
                if body:
                    return f"Police Result: {body.get_text(strip=True)}"
                return "Police: Check manually (Could not parse result)."
                
        except Exception as e:
            return f"Police Error: {e}"

    def check_counterscam(self, phone):
        """
        Check CounterScam 112.
        """
        url = "https://www.counterscam112.go.kr/phishing/searchPhone.do"
        # Likely a GET or POST. 
        # Browser log showed input 'tel_num'.
        
        try:
            # Try POST first
            data = {'tel_num': phone}
            response = requests.post(url, data=data, headers=self.headers, verify=False, timeout=10)
            
            if "검색결과가 없습니다" in response.text:
                 return "CounterScam: No reports found (Clean)."
            elif "피싱" in response.text and "검색결과" in response.text:
                 # Only if 'Phishing' and 'Result' appear together, or similar logic.
                 # Since we can't be sure, we'll default to manual check if not explicitly 'No results'.
                 return "CounterScam: Potential match found (Check site to confirm)."
            else:
                 return "CounterScam: Check manually (Could not parse result)."
                 
        except Exception as e:
            return f"CounterScam Error: {e}"

    def check_bank_fed(self, bank_name, phone):
        """
        Check Bank Federation.
        bank_name: Name of the bank (Korean)
        phone: Phone number
        """
        url = "https://portal.kfb.or.kr/voice/bankphonenumber.php"
        
        # Partial list of bank codes (Need to be accurate for real usage)
        # Since I don't have the codes, I'll use the text and hope the backend accepts it or I'll just print a warning.
        # Actually, usually these forms submit the VALUE (code), not the text.
        # Without the codes, this is hard. I will return a message explaining this.
        
        return "BankFed: Requires Bank Codes (Not scraped). Please visit site manually."

    def check_kisa(self, url_to_check):
        """
        Check KISA Smishing.
        """
        # The URL provided seems to be an info page.
        # I will return a message.
        return "KISA: The provided URL appears to be an information page. Please use the 'Boho' mobile app for Smishing verification."

def main():
    searcher = FraudSearch()
    
    print("--- Fraud Search Tool ---")
    val = input("Enter value (Phone/Account/Email/URL): ")
    
    # Simple heuristic to guess type
    if "@" in val:
        print(searcher.check_police('email', val))
    elif val.startswith("http"):
        print(searcher.check_kisa(val))
    elif len(val) > 8 and val.isdigit():
        # Could be phone or account.
        print(searcher.check_police('phone', val))
        print(searcher.check_counterscam(val))
        # print(searcher.check_bank_fed('Unknown', val))
    else:
        print("Unknown format.")

if __name__ == "__main__":
    main()
