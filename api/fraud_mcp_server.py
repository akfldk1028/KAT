from mcp.server.fastmcp import FastMCP
import requests
from bs4 import BeautifulSoup
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create the MCP server
mcp = FastMCP("Fraud Check Server")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

@mcp.tool()
def check_police_db(search_type: str, value: str) -> str:
    """
    Search the Korean National Police Agency's Cyber Bureau database for reported fraud.
    
    Args:
        search_type: One of "phone", "account", or "email".
        value: The phone number, account number, or email address to check.
    """
    url = "https://www.police.go.kr/user/search/ND_searchResult.do"
    
    type_map = {
        'phone': '1',
        'account': '2',
        'email': '3'
    }
    
    target = type_map.get(search_type.lower())
    if not target:
        return "Error: Invalid search_type. Must be 'phone', 'account', or 'email'."

    data = {
        'colTarget': target,
        'searchTerm': value,
        'search': 'true'
    }

    try:
        response = requests.post(url, data=data, headers=HEADERS, verify=False, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if "접수된 민원이 없습니다" in response.text or "검색결과가 없습니다" in response.text:
            return "Police DB: No reports found (Clean)."
        elif "신고된 번호입니다" in response.text:
            return "Police DB: REPORTED! Caution required."
        else:
            # Try to extract a result snippet
            body = soup.find('div', {'class': 'result_box'})
            if body:
                return f"Police DB Result: {body.get_text(strip=True)}"
            return "Police DB: Check manually (Could not parse result)."
            
    except Exception as e:
        return f"Police DB Error: {str(e)}"

@mcp.tool()
def check_counterscam(phone_number: str) -> str:
    """
    Search the CounterScam 112 database for phishing phone numbers.
    
    Args:
        phone_number: The phone number to check (digits only preferred).
    """
    url = "https://www.counterscam112.go.kr/phishing/searchPhone.do"
    
    try:
        data = {'tel_num': phone_number}
        response = requests.post(url, data=data, headers=HEADERS, verify=False, timeout=10)
        
        if "검색결과가 없습니다" in response.text:
             return "CounterScam: No reports found (Clean)."
        elif "피싱" in response.text and "검색결과" in response.text:
             return "CounterScam: Potential match found (Check site to confirm)."
        else:
             return "CounterScam: Check manually (Could not parse result)."
             
    except Exception as e:
        return f"CounterScam Error: {str(e)}"

if __name__ == "__main__":
    # Run the server using stdio transport
    mcp.run(transport='stdio')
