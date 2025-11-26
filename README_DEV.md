# Kanana DualGuard POC - 개발자 가이드

> **양방향 메시지 보안 시스템 (Outgoing + Incoming Agent)**

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 1. 가상환경 활성화
cd backend
.\venv\Scripts\activate

# 2. FastAPI 서버 시작
./venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# 3. Node.js 서버 시작 (새 터미널)
cd frontend/KakaoTalk/server
npm start
```

### 2. 테스트

```bash
# 통합 테스트
cd backend
./venv/Scripts/python.exe ../test_integration.py
```

## 📚 문서

- **[테스트 가이드](./TESTING_GUIDE.md)** - 어떻게 테스트하는지
- **[유지보수 가이드](./MAINTENANCE_GUIDE.md)** - 어떻게 수정/확장하는지

## 🏗️ 아키텍처

```
Client → Node.js (Socket.io) → FastAPI (Agent API)
                                   ├─ AgentManager (딕셔너리)
                                   │   ├─ OutgoingAgent
                                   │   └─ IncomingAgent
                                   └─ LLMManager (딕셔너리)
                                       └─ Kanana Safeguard
```

## 🔑 핵심 개념

### AgentManager (딕셔너리 패턴)
```python
from agent.agent_manager import AgentManager

# Agent 가져오기 (Lazy Loading + Singleton)
agent = AgentManager.get("outgoing")
result = agent.analyze("계좌번호 123-45-67890")
```

### LLMManager (딕셔너리 패턴)
```python
from agent.llm_manager import LLMManager

# LLM 가져오기 (필요할 때만 로드)
llm = LLMManager.get("safeguard")
```

## 📝 새 Agent 추가 (3단계)

### 1. Agent 클래스 생성
```python
# agent/spam.py
class SpamAgent:
    def analyze(self, text: str) -> AnalysisResponse:
        # 구현
        pass
```

### 2. AgentManager에 등록
```python
# agent/agent_manager.py
_registry = {
    "outgoing": OutgoingAgent,
    "incoming": IncomingAgent,
    "spam": SpamAgent,  # 추가
}
```

### 3. API 엔드포인트 추가
```python
# backend/app/routers/agents.py
@router.post("/analyze/spam")
async def analyze_spam(request: MessageAnalysisRequest):
    agent = AgentManager.get("spam")
    return agent.analyze(request.text)
```

## 🧪 테스트 체크리스트

- [ ] 가상환경 활성화 확인
- [ ] FastAPI 서버 실행 (포트 8000)
- [ ] Node.js 서버 실행 (포트 8001)
- [ ] `/api/agents/health` 응답 확인
- [ ] `test_integration.py` 통과

## 📦 디렉토리 구조

```
KAT/
├── agent/                      # Agent 모듈
│   ├── agent_manager.py       # Agent 중앙 관리
│   ├── llm_manager.py         # LLM 중앙 관리
│   ├── outgoing.py            # 안심 전송 Agent
│   ├── incoming.py            # 안심 가드 Agent
│   └── tools.py               # MCP Tools
│
├── backend/                    # FastAPI 서버
│   └── app/routers/
│       └── agents.py          # Agent API 라우터
│
├── frontend/KakaoTalk/        # 채팅 UI
│   ├── client/                # React
│   └── server/                # Node.js + Socket.io
│
├── test_api.py                # API 테스트
├── test_integration.py        # 통합 테스트
├── TESTING_GUIDE.md           # 테스트 가이드
└── MAINTENANCE_GUIDE.md       # 유지보수 가이드
```

## 🛠️ 유용한 명령어

```bash
# Agent 목록 확인
python -c "from agent.agent_manager import AgentManager; print(AgentManager.list_agents())"

# FastAPI 문서
http://localhost:8000/docs

# 빠른 테스트
curl http://localhost:8000/api/agents/health
```

## 🐛 트러블슈팅

### 문제: ModuleNotFoundError
```bash
# 해결: 가상환경 활성화
cd backend
.\venv\Scripts\activate
```

### 문제: 포트 충돌
```bash
# 해결: 다른 포트 사용
uvicorn app.main:app --port 8001
```

자세한 내용은 [TESTING_GUIDE.md](./TESTING_GUIDE.md) 참조

## 📞 문의

- 테스트 방법: [TESTING_GUIDE.md](./TESTING_GUIDE.md)
- 유지보수: [MAINTENANCE_GUIDE.md](./MAINTENANCE_GUIDE.md)
- 제안서: [제안서.pdf](./제안서.pdf)
