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

## 필수 요구사항

*   Python 3.10 이상
*   `mcp` 패키지
*   `requests`
*   `beautifulsoup4`

## 설치 방법

필요한 라이브러리를 설치합니다:

```bash
pip install mcp requests beautifulsoup4
```

## 사용 방법

이 서버는 `stdio` (표준 입출력) 방식을 사용하여 MCP 클라이언트(예: Claude Desktop, IDE 확장 프로그램 등)와 통신합니다.

### 서버 실행 명령어
```bash
python fraud_mcp_server.py
```

### 클라이언트 설정 예시 (Claude Desktop)

Claude Desktop 설정 파일(`claude_desktop_config.json`)에 다음과 같이 추가하여 사용할 수 있습니다:

```json
{
  "mcpServers": {
    "fraud-check": {
      "command": "python",
      "args": ["D:\\project\\AIAgentcompetition\\testdata\\KAT\\api\\fraud_mcp_server.py"]
    }
  }
}
```
*주의: `args`의 파일 경로는 실제 `fraud_mcp_server.py` 파일이 위치한 절대 경로로 수정해야 합니다.*
