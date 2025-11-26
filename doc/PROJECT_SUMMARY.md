# Kanana DualGuard Project Summary & Guide

## 1. 프로젝트 개요 (Project Overview)
**Kanana DualGuard**는 카카오톡 환경에서 발생하는 보안 위협을 방지하기 위한 양방향 AI 보안 에이전트 시스템입니다.
- **Outgoing Agent (안심 전송)**: 메시지 발신 시 계좌번호, 주민번호 등 민감정보를 감지하여 "시크릿 전송"을 제안합니다.
- **Incoming Agent (안심 가드)**: 메시지 수신 시 피싱, 가족 사칭, 급전 요구 등을 감지하여 경고를 표시합니다.

## 2. 시스템 구조 (System Architecture)
이 프로젝트는 **3-Tier Architecture**로 구성되어 있으며, 프론트엔드 폴더 내에 Node.js 서버가 포함된 구조입니다.

1.  **Frontend Client (React)**
    - **위치**: `frontend/KakaoTalk/client` (Port: 3000)
    - **역할**: 사용자 UI/UX 담당.
2.  **Frontend Server (Node.js)**
    - **위치**: `frontend/KakaoTalk/server` (Port: 8001)
    - **역할**: 메인 서버. 채팅, 친구 관리, DB 연결, 실시간 통신(Socket.io)을 담당하며, 보안 분석이 필요할 때 Python Backend로 요청을 보냅니다.
3.  **Backend (Python/FastAPI)**
    - **위치**: `backend` (Port: 8002)
    - **역할**: AI 보안 분석 전용 서버. 텍스트 분석 및 LLM 모델을 구동합니다.

## 3. 현재 구현 상태 (Current Status)
- **Backend (FastAPI)**: 
    - 포트: `8002`
    - 역할: 보안 에이전트 로직 수행, 텍스트 분석 API 제공.
    - 상태: 정상 작동 (AgentManager, Outgoing/Incoming Agent 구현 완료).
- **Middleware (Node.js)**:
    - 포트: `8001`
    - 역할: 클라이언트와 백엔드 간의 중계, 채팅/친구 데이터 관리, Socket.io 실시간 통신.
    - 상태: 정상 작동 (Backend 포트 8002로 연동 완료).
- **Frontend (React)**:
    - 포트: `3000`
    - 역할: 사용자 인터페이스 (친구 목록, 채팅방, 보안 경고 표시).
    - 상태: 정상 작동 (Node.js v22 호환성 패치 적용 완료).
- **AI Integration**:
    - MCP(Model Context Protocol) 도구 구현 완료 (`analyze_outgoing`, `analyze_incoming`).
    - Kanana LLM 연동 구조 마련 (현재 Rule-based 우선 동작, 설정 시 LLM 호출 가능).

## 4. 설치 및 실행 방법 (Installation & Execution)

### 4.1 사전 요구사항
- Python 3.8 이상
- Node.js (v14 이상 권장, v22 호환성 확인됨)

### 4.2 실행 순서 (터미널 3개 필요)

**Step 1: Backend (FastAPI) 실행**
```bash
cd backend
# 가상환경 활성화 (Windows)
.\venv\Scripts\activate
# 서버 시작 (포트 8002)
$env:PYTHONPATH=".."; python -m uvicorn app.main:app --port 8002
```

**Step 2: Middleware (Node.js) 실행**
```bash
cd frontend/KakaoTalk/server
npm start
# 포트 8001에서 실행됨
```

**Step 3: Frontend (React) 실행**
```bash
cd frontend/KakaoTalk/client
# Node.js v17+ 사용 시 호환성 옵션 필요
$env:NODE_OPTIONS="--openssl-legacy-provider"; npm start
# 포트 3000에서 실행됨 (브라우저 자동 실행)
```

## 5. MCP (Model Context Protocol) 가이드

### 5.1 MCP와 채팅방의 관계
**"채팅방과 MCP는 서로 다른 문(Door)입니다."**
- **채팅방 (Web App)**: 사용자가 입력한 메시지는 **Node.js 서버**를 통해 **Python API(8002)**로 전달되어 분석됩니다.
- **MCP 서버**: Claude 같은 **외부 AI**가 프로젝트의 보안 도구(`analyze_outgoing` 등)를 사용할 수 있게 열어둔 **별도의 문**입니다.
- **공통점**: 둘 다 똑같은 **보안 에이전트 로직(Agent Logic)**을 사용합니다.

### 5.2 MCP 테스트 방법 (Claude Desktop 사용 시)
MCP 서버가 정상적으로 켜져 있다면, Claude Desktop 설정 파일에 등록하여 테스트할 수 있습니다.

**설정 파일 경로**:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**설정 내용**:
```json
{
  "mcpServers": {
    "kanana-dualguard": {
      "command": "d:\\Data\\18_KAT\\KAT\\backend\\venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "agent.mcp.server"
      ],
      "env": {
        "PYTHONPATH": "d:\\Data\\18_KAT\\KAT"
      }
    }
  }
}
```
**테스트 시나리오**:
1. Claude Desktop을 켭니다.
2. Claude에게 물어봅니다: *"이 메시지 안전한지 분석해줘: '엄마 나 폰 고장났어 돈 좀 보내줘'"*
3. Claude가 `analyze_incoming` 도구를 사용하여 분석 결과를 보여주면 성공입니다.

## 6. 웹 채팅 테스트 가이드 (Testing Guide)

### 6.1 접속 주소
- 프론트엔드: http://localhost:3000

### 6.2 시나리오 테스트
1.  **회원가입 및 로그인**: 임의의 아이디로 가입 후 로그인합니다.
2.  **안심 전송 (Outgoing) 테스트**:
    - 채팅방에서 `123-45-67890`과 같은 계좌번호 형식을 입력하고 전송을 시도합니다.
    - **결과**: "시크릿 전송"을 추천하는 알림이나 상태가 표시되어야 합니다.
3.  **안심 가드 (Incoming) 테스트**:
    - "엄마 나 폰 고장났어 돈 좀 보내줘"와 같은 사칭 메시지를 받습니다.
    - **결과**: 위험 경고(빨간색/노란색)가 표시되어야 합니다.

### 6.3 멀티 유저 채팅 테스트 (창 2개 띄우기)
한 컴퓨터에서 두 명의 사용자로 대화하려면:
1.  **창 1**: 일반 브라우저에서 `http://localhost:3000` 접속 -> **User A** 로그인.
2.  **창 2**: **시크릿 모드(Incognito)**에서 `http://localhost:3000` 접속 -> **User B** 로그인.
3.  **연결**: User A가 User B를 친구 추가하고 채팅방을 생성합니다.
4.  **대화**: 메시지를 주고받으며 실시간 전송과 보안 분석 결과를 확인합니다.

## 7. 트러블슈팅 (Troubleshooting)
- **포트 충돌**: `8000`번 포트가 사용 중이라 Backend를 `8002`로 변경했습니다. 모든 설정 파일(`agentService.ts` 등)이 `8002`를 가리키는지 확인하세요.
- **Frontend 실행 오류**: `ERR_OSSL_EVP_UNSUPPORTED` 에러 발생 시, 반드시 `$env:NODE_OPTIONS="--openssl-legacy-provider"` 옵션을 주고 실행해야 합니다.
- **DB 오류**: `sqlite3` 관련 에러가 나면 `frontend/KakaoTalk/server` 폴더의 `kanana_dualguard.db` (또는 유사 파일) 권한을 확인하거나 삭제 후 재시작하세요.
