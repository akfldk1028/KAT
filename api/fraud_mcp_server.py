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

@mcp.tool()
def check_google_safe_browsing(url: str) -> str:
    """
    Check a URL against Google Safe Browsing API (Malware/Phishing).
    Requires 'GOOGLE_API_KEY' environment variable.
    """
    import os
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        return "Error: 'GOOGLE_API_KEY' environment variable is missing. Please set it to use this tool."

    api_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
    
    payload = {
        "client": {
            "clientId": "mcp-fraud-check",
            "clientVersion": "1.0.0"
        },
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }

    try:
        response = requests.post(api_url, json=payload, headers=HEADERS, timeout=10)
        data = response.json()
        
        matches = data.get('matches', [])
        if not matches:
            return "Google Safe Browsing: No threats found (Clean)."
        else:
            threats = [m.get('threatType') for m in matches]
            return f"Google Safe Browsing: WARNING! Threats detected: {', '.join(threats)}"
            
    except Exception as e:
        return f"Google Safe Browsing Error: {str(e)}"

@mcp.tool()
def check_virustotal(url: str) -> str:
    """
    Check a URL against VirusTotal API.
    Requires 'VIRUSTOTAL_API_KEY' environment variable.
    """
    import os
    api_key = os.environ.get('VIRUSTOTAL_API_KEY')
    if not api_key:
        return "Error: 'VIRUSTOTAL_API_KEY' environment variable is missing. Please set it to use this tool."

    # Using v2 API for simplicity in URL reporting
    api_url = "https://www.virustotal.com/vtapi/v2/url/report"
    params = {'apikey': api_key, 'resource': url}

    try:
        response = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
        
        if response.status_code == 204:
            return "VirusTotal: Rate limit exceeded. Please try again later."
        elif response.status_code == 403:
            return "VirusTotal: Invalid API Key."
            
        data = response.json()
        
        if data.get('response_code') == 0:
            return "VirusTotal: URL not found in database (No previous scan)."
        
        positives = data.get('positives', 0)
        total = data.get('total', 0)
        scan_date = data.get('scan_date', 'Unknown')
        
        if positives > 0:
            return f"VirusTotal: WARNING! {positives}/{total} engines detected this URL as malicious. (Scanned: {scan_date})"
        else:
            return f"VirusTotal: Clean. 0/{total} engines detected this URL. (Scanned: {scan_date})"

    except Exception as e:
        return f"VirusTotal Error: {str(e)}"

if __name__ == "__main__":
    # Run the server using stdio transport
    mcp.run(transport='stdio')
