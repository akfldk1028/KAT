# 사기 피해 방지 MCP 서버 (Fraud Check MCP Server)

이 프로젝트는 한국의 주요 사기 피해 방지 데이터베이스를 조회할 수 있는 도구를 제공하는 MCP(Model Context Protocol) 서버입니다.

## 주요 기능

다음과 같은 도구(Tools)를 제공합니다:

1.  **`check_police_db`**: 경찰청 사이버수사국 '사이버 사기' 데이터베이스를 조회합니다.
    *   **인자 (Arguments)**:
        *   `search_type`: 검색 유형 (`phone`=전화번호, `account`=계좌번호, `email`=이메일)
        *   `value`: 검색할 번호 또는 이메일 주소
2.  **`check_counterscam`**: 경찰청 '피싱 전화번호' 데이터베이스(CounterScam 112)를 조회합니다.
    *   **인자 (Arguments)**:
        *   `phone_number`: 조회할 전화번호 (숫자만 입력 권장)

3.  **`check_google_safe_browsing`**: Google Safe Browsing API를 통해 악성/피싱 URL 여부를 확인합니다.
    *   **인자**: `url`
    *   **필수**: `GOOGLE_API_KEY` 환경 변수
4.  **`check_virustotal`**: VirusTotal API를 통해 URL의 악성 여부를 검사합니다.
    *   **인자**: `url`
    *   **필수**: `VIRUSTOTAL_API_KEY` 환경 변수

## 필수 요구사항

*   Python 3.10 이상
*   `mcp` 패키지
*   `requests`
*   `beautifulsoup4`
*   **API 키**: Google Cloud Console 및 VirusTotal에서 발급받은 API 키

## 설치 방법

필요한 라이브러리를 설치합니다:

```bash
pip install mcp requests beautifulsoup4
```

## 환경 변수 설정 (API 키)

URL 검사 기능을 사용하려면 API 키를 환경 변수로 설정해야 합니다.

*   **Google Safe Browsing**: [Google Cloud Console](https://console.cloud.google.com/)에서 'Safe Browsing API'를 활성화하고 API 키를 생성합니다.
*   **VirusTotal**: [VirusTotal](https://www.virustotal.com/) 회원가입 후 API 키를 확인합니다.

### Claude Desktop 설정 예시

`claude_desktop_config.json` 파일의 `env` 섹션에 키를 추가합니다:

```json
{
  "mcpServers": {
    "fraud-check": {
      "command": "python",
      "args": ["D:\\project\\AIAgentcompetition\\testdata\\KAT\\api\\fraud_mcp_server.py"],
      "env": {
        "GOOGLE_API_KEY": "여기에_구글_API_키_입력",
        "VIRUSTOTAL_API_KEY": "여기에_바이러스토탈_API_키_입력"
      }
    }
  }
}
```
*주의: `args`의 파일 경로는 실제 `fraud_mcp_server.py` 파일이 위치한 절대 경로로 수정해야 합니다.*
