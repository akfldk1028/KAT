# Kanana DualGuard 유지보수 가이드

> **모듈화된 아키텍처로 쉽게 확장하고 유지보수하세요**

## 목차

1. [프로젝트 아키텍처](#1-프로젝트-아키텍처)
2. [새 Agent 추가하기](#2-새-agent-추가하기)
3. [기존 Agent 수정하기](#3-기존-agent-수정하기)
4. [LLM 모델 관리](#4-llm-모델-관리)
5. [API 엔드포인트 추가](#5-api-엔드포인트-추가)
6. [배포 전 체크리스트](#6-배포-전-체크리스트)
7. [코드 스타일 가이드](#7-코드-스타일-가이드)

---

## 1. 프로젝트 아키텍처

### 1.1 디렉토리 구조

```
KAT/
├── agent/                          # Agent 모듈
│   ├── agent_manager.py           # ✅ Agent 중앙 관리
│   ├── llm_manager.py             # ✅ LLM 중앙 관리
│   ├── outgoing.py                # 안심 전송 Agent
│   ├── incoming.py                # 안심 가드 Agent
│   ├── models.py                  # 공통 데이터 모델
│   └── tools.py                   # MCP Tools
│
├── backend/                        # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py               # FastAPI 앱 진입점
│   │   └── routers/
│   │       └── agents.py         # ✅ Agent API 라우터
│   └── venv/                     # Python 가상환경
│
├── frontend/KakaoTalk/            # 채팅 UI
│   ├── client/                   # React 클라이언트
│   └── server/                   # Node.js + Socket.io
│       └── src/
│           ├── services/
│           │   └── agentService.ts  # ✅ Agent API 클라이언트
│           └── sockets/
│               └── index.ts      # ✅ Socket.io + Agent 통합
│
├── test_api.py                   # API 테스트
├── test_integration.py           # 통합 테스트
└── test_kanana_safeguard.py     # LLM 테스트
```

### 1.2 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                    Client (React)                            │
│                  Socket.io-client                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Node.js Server (포트 8001)                      │
│  ┌──────────────────────────────────────────────┐           │
│  │  Socket.io Handler                           │           │
│  │  ├─ message event                            │           │
│  │  │   ↓                                       │           │
│  │  └─ agentService.analyzeOutgoing() ─────────┼──┐        │
│  └──────────────────────────────────────────────┘  │        │
└─────────────────────────────────────────────────────┼────────┘
                                                      │ HTTP
                                                      ↓
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Server (포트 8000)                      │
│  ┌──────────────────────────────────────────────┐           │
│  │  Agent API Router                            │           │
│  │  ├─ POST /api/agents/analyze/outgoing       │           │
│  │  ├─ POST /api/agents/analyze/incoming       │           │
│  │  └─ GET  /api/agents/health                 │           │
│  └────────────────────┬─────────────────────────┘           │
│                       │                                      │
│                       ↓                                      │
│  ┌──────────────────────────────────────────────┐           │
│  │         AgentManager (딕셔너리)              │           │
│  │  {                                           │           │
│  │    "outgoing": OutgoingAgent,               │           │
│  │    "incoming": IncomingAgent                │           │
│  │  }                                           │           │
│  └────────────────────┬─────────────────────────┘           │
│                       │                                      │
│         ┌─────────────┴─────────────┐                      │
│         ↓                           ↓                      │
│  ┌─────────────┐            ┌──────────────┐              │
│  │  Outgoing   │            │   Incoming   │              │
│  │   Agent     │            │    Agent     │              │
│  │ (Rule-based)│            │ (Rule-based) │              │
│  └─────────────┘            └──────┬───────┘              │
│                                     │                       │
│                                     ↓                       │
│                          ┌─────────────────────┐           │
│                          │   LLMManager        │           │
│                          │   (딕셔너리)        │           │
│                          │  {                  │           │
│                          │    "safeguard":     │           │
│                          │      KananaLLM      │           │
│                          │  }                  │           │
│                          └─────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 핵심 개념

#### AgentManager (딕셔너리 패턴)
- **역할**: 모든 Agent를 중앙에서 관리
- **특징**:
  - Registry 패턴으로 Agent 등록
  - Lazy Loading (필요할 때만 생성)
  - Singleton (재사용)

#### LLMManager (딕셔너리 패턴)
- **역할**: 모든 LLM 모델을 중앙에서 관리
- **특징**:
  - Lazy Loading (필요할 때만 로드)
  - 메모리 효율성 (8GB 모델 관리)

---

## 2. 새 Agent 추가하기

### 시나리오: "SpamAgent" 추가

#### Step 1: Agent 클래스 생성

`agent/spam.py` 생성:

```python
"""
Spam Detection Agent
스팸 메시지를 감지하는 Agent
"""

from .models import AnalysisResponse, RiskLevel
import re

class SpamAgent:
    """스팸 감지 Agent"""

    def analyze(self, text: str) -> AnalysisResponse:
        """
        스팸 메시지 분석

        Args:
            text: 분석할 메시지

        Returns:
            AnalysisResponse: 분석 결과
        """
        reasons = []
        risk_level = RiskLevel.LOW

        # 스팸 키워드 패턴
        spam_keywords = ["대출", "무료", "당첨", "클릭", "즉시", "환급"]
        found_keywords = [kw for kw in spam_keywords if kw in text]

        if found_keywords:
            reasons.append(f"스팸 키워드 감지: {', '.join(found_keywords)}")
            risk_level = RiskLevel.MEDIUM

        # URL 패턴 (의심스러운 링크)
        if re.search(r'http[s]?://bit\.ly|goo\.gl', text):
            reasons.append("단축 URL이 감지되었습니다.")
            risk_level = RiskLevel.HIGH

        recommended_action = "차단" if risk_level == RiskLevel.HIGH else "표시"

        return AnalysisResponse(
            risk_level=risk_level,
            reasons=reasons,
            recommended_action=recommended_action,
            is_secret_recommended=False
        )
```

#### Step 2: AgentManager에 등록

`agent/agent_manager.py` 수정:

```python
from .spam import SpamAgent  # 추가

class AgentManager:
    _registry: Dict[str, Type] = {
        "outgoing": OutgoingAgent,
        "incoming": IncomingAgent,
        "spam": SpamAgent,  # 추가
    }

    # ... (기존 코드)

    @classmethod
    def get_spam(cls) -> SpamAgent:
        """스팸 감지 Agent 가져오기"""
        return cls.get("spam")
```

#### Step 3: FastAPI 라우터에 엔드포인트 추가

`backend/app/routers/agents.py` 수정:

```python
@router.post("/analyze/spam", response_model=MessageAnalysisResponse)
async def analyze_spam_message(request: MessageAnalysisRequest):
    """
    스팸 감지 Agent - 스팸 메시지 분석

    Args:
        request: 메시지 분석 요청

    Returns:
        분석 결과 (위험도, 이유, 권장 조치)
    """
    try:
        spam_agent = AgentManager.get_spam()
        result = spam_agent.analyze(request.text)

        return MessageAnalysisResponse(
            risk_level=result.risk_level.value,
            reasons=result.reasons,
            recommended_action=result.recommended_action,
            is_secret_recommended=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spam analysis failed: {str(e)}")
```

#### Step 4: 테스트 작성

```python
# 테스트 코드
from agent.agent_manager import AgentManager

agent = AgentManager.get_spam()
result = agent.analyze("무료 대출 즉시 승인! http://bit.ly/xxx 클릭")

print(f"위험도: {result.risk_level}")
print(f"이유: {result.reasons}")
# 예상: MEDIUM 또는 HIGH
```

#### Step 5: API 테스트

```bash
cd backend
./venv/Scripts/python.exe -c "
import requests
response = requests.post(
    'http://127.0.0.1:8000/api/agents/analyze/spam',
    json={'text': '무료 대출 즉시 승인!'}
)
print(response.json())
"
```

---

## 3. 기존 Agent 수정하기

### 시나리오: OutgoingAgent에 신용카드 번호 감지 추가

#### Step 1: Agent 코드 수정

`agent/outgoing.py`:

```python
def analyze(self, text: str) -> AnalysisResponse:
    reasons = []
    risk_level = RiskLevel.LOW
    is_secret_recommended = False

    # 기존 패턴들...

    # 신용카드 번호 (새로 추가)
    if re.search(r'\d{4}-\d{4}-\d{4}-\d{4}', text):
        reasons.append("신용카드 번호 패턴이 감지되었습니다.")
        risk_level = RiskLevel.HIGH
        is_secret_recommended = True

    # ...
```

#### Step 2: 테스트

```python
from agent.agent_manager import AgentManager

agent = AgentManager.get_outgoing()
result = agent.analyze("카드번호 1234-5678-9012-3456")

print(f"위험도: {result.risk_level}")  # HIGH
print(f"시크릿 전송 추천: {result.is_secret_recommended}")  # True
```

#### Step 3: 회귀 테스트

기존 테스트가 여전히 통과하는지 확인:

```bash
cd backend
./venv/Scripts/python.exe ../test_api.py
```

---

## 4. LLM 모델 관리

### 4.1 새 모델 추가

`agent/llm_manager.py`:

```python
class KananaLLM:
    def __init__(self, model_type: str = "instruct"):
        if model_type == "safeguard":
            self.model_id = "kakaocorp/kanana-safeguard-8b"
        elif model_type == "chat":  # 새 모델 추가
            self.model_id = "kakaocorp/Kanana-Chat-7b"
        else:
            self.model_id = "kakaocorp/Kanana-Nano-2.1b-instruct"
```

### 4.2 모델 버전 업그레이드

```python
# 이전
self.model_id = "kakaocorp/kanana-safeguard-8b"

# 새 버전
self.model_id = "kakaocorp/kanana-safeguard-8b-v2"
```

### 4.3 모델 메모리 관리

```python
from agent.llm_manager import LLMManager

# 모델 언로드 (메모리 해제)
LLMManager.unload("safeguard")

# 모든 모델 언로드
LLMManager.unload_all()

# 다시 로드 (자동)
llm = LLMManager.get("safeguard")  # 필요 시 자동 로드
```

---

## 5. API 엔드포인트 추가

### 5.1 배치 분석 엔드포인트 추가

`backend/app/routers/agents.py`:

```python
class BatchAnalysisRequest(BaseModel):
    """배치 분석 요청"""
    messages: List[str]

class BatchAnalysisResponse(BaseModel):
    """배치 분석 응답"""
    results: List[MessageAnalysisResponse]

@router.post("/analyze/outgoing/batch", response_model=BatchAnalysisResponse)
async def analyze_outgoing_batch(request: BatchAnalysisRequest):
    """
    여러 메시지를 한 번에 분석
    """
    try:
        outgoing_agent = AgentManager.get_outgoing()
        results = []

        for text in request.messages:
            result = outgoing_agent.analyze(text)
            results.append(MessageAnalysisResponse(
                risk_level=result.risk_level.value,
                reasons=result.reasons,
                recommended_action=result.recommended_action,
                is_secret_recommended=result.is_secret_recommended
            ))

        return BatchAnalysisResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 5.2 테스트

```bash
cd backend
./venv/Scripts/python.exe -c "
import requests
response = requests.post(
    'http://127.0.0.1:8000/api/agents/analyze/outgoing/batch',
    json={
        'messages': [
            '계좌번호 123-45-67890',
            '일반 메시지',
            '주민번호 900101-1234567'
        ]
    }
)
print(response.json())
"
```

---

## 6. 배포 전 체크리스트

### 6.1 코드 품질

- [ ] 모든 함수에 docstring 작성
- [ ] 타입 힌트 추가 (Python 3.8+)
- [ ] 린터 실행 (`flake8`, `pylint`)
- [ ] 포매터 실행 (`black`)

### 6.2 테스트

- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과 (`test_integration.py`)
- [ ] API 테스트 통과 (`test_api.py`)
- [ ] 회귀 테스트 통과

### 6.3 보안

- [ ] 민감정보 하드코딩 확인 (API 키, 비밀번호)
- [ ] `.env` 파일 사용
- [ ] `.gitignore`에 민감 파일 추가

### 6.4 성능

- [ ] 메모리 사용량 확인
- [ ] API 응답 시간 확인 (<2초)
- [ ] LLM 로딩 시간 최적화

### 6.5 문서

- [ ] README 업데이트
- [ ] API 문서 업데이트 (`/docs`)
- [ ] CHANGELOG 작성

---

## 7. 코드 스타일 가이드

### 7.1 Python (PEP 8)

```python
# Good
class OutgoingAgent:
    """안심 전송 Agent"""

    def analyze(self, text: str) -> AnalysisResponse:
        """메시지 분석"""
        pass

# Bad
class outgoing_agent:  # 클래스명은 CamelCase
    def Analyze(self, text):  # 메서드명은 snake_case, 타입 힌트 누락
        pass
```

### 7.2 TypeScript (Airbnb Style)

```typescript
// Good
class AgentService {
  async analyzeOutgoing(text: string): Promise<SecurityAnalysis> {
    const response = await axios.post(API_URL, { text });
    return response.data;
  }
}

// Bad
class agent_service {  // 클래스명은 PascalCase
  analyzeOutgoing(text) {  // 타입 정의 누락
    return axios.post(API_URL, { text });  // async/await 없음
  }
}
```

### 7.3 주석 스타일

```python
# Good
"""
Kanana DualGuard Agent
민감정보 감지 및 보안 위협 탐지

모듈화된 아키텍처로 쉽게 확장 가능
"""

# Bad
# This is agent  # 불충분한 설명
```

---

## 8. 일반적인 유지보수 시나리오

### 시나리오 1: 버그 수정

1. 문제 재현
2. 테스트 케이스 작성 (실패하는 테스트)
3. 코드 수정
4. 테스트 통과 확인
5. 회귀 테스트

### 시나리오 2: 성능 최적화

1. 프로파일링 (`cProfile`, `memory_profiler`)
2. 병목 지점 확인
3. 최적화 (캐싱, 비동기 처리 등)
4. 벤치마크 비교
5. 테스트

### 시나리오 3: 보안 패치

1. 취약점 확인
2. 패치 적용
3. 보안 테스트
4. 긴급 배포

---

## 9. 유용한 명령어 모음

```bash
# Agent 목록 확인
python -c "from agent.agent_manager import AgentManager; print(AgentManager.list_agents())"

# 특정 Agent 테스트
python -c "from agent.agent_manager import AgentManager; print(AgentManager.get('outgoing').analyze('test'))"

# FastAPI 문서 확인
# 브라우저에서: http://localhost:8000/docs

# 로그 확인 (FastAPI)
tail -f backend/logs/app.log

# 메모리 사용량 확인
ps aux | grep python

# 포트 확인
netstat -ano | findstr :8000
```

---

## 10. 도움말 및 참고 자료

- **테스트 가이드**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)
- **FastAPI 문서**: https://fastapi.tiangolo.com/
- **Kanana 모델**: https://huggingface.co/kakaocorp
- **MCP 프로토콜**: https://modelcontextprotocol.io/

---

## 문의 및 이슈 보고

문제가 발생하면:
1. 로그 확인
2. [TESTING_GUIDE.md](./TESTING_GUIDE.md) 트러블슈팅 참조
3. 재현 가능한 테스트 케이스 작성
4. 이슈 보고
