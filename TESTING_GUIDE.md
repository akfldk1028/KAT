# Kanana DualGuard 테스트 가이드

> **⚠️ 중요: 모든 테스트는 가상환경을 활성화한 상태에서 실행해야 합니다!**

## 목차

1. [환경 설정 확인](#1-환경-설정-확인)
2. [Agent 단위 테스트](#2-agent-단위-테스트)
3. [LLM 모델 테스트](#3-llm-모델-테스트)
4. [FastAPI 서버 테스트](#4-fastapi-서버-테스트)
5. [Node.js 서버 테스트](#5-nodejs-서버-테스트)
6. [통합 테스트](#6-통합-테스트)
7. [트러블슈팅](#7-트러블슈팅)

---

## 1. 환경 설정 확인

### 1.1 가상환경 활성화

```bash
# Windows
cd D:\Data\18_KAT\KAT\backend
.\venv\Scripts\activate

# 확인: 프롬프트 앞에 (venv)가 표시되어야 함
```

### 1.2 Python 버전 확인

```bash
python --version
# 예상 결과: Python 3.8 이상
```

### 1.3 필수 패키지 설치 확인

```bash
pip list | grep -E "fastapi|transformers|torch"
# 또는 Windows에서
pip list | findstr "fastapi transformers torch"
```

**예상 결과:**
```
fastapi                   0.xxx
torch                     2.x.x
transformers              4.x.x
```

---

## 2. Agent 단위 테스트

### 2.1 AgentManager 테스트

```python
# Python 인터프리터 실행
python

# 테스트 코드
from agent.agent_manager import AgentManager

# Outgoing Agent 가져오기
outgoing = AgentManager.get_outgoing()
print(outgoing)  # <agent.outgoing.OutgoingAgent object ...>

# Incoming Agent 가져오기
incoming = AgentManager.get_incoming()
print(incoming)  # <agent.incoming.IncomingAgent object ...>

# 등록된 Agent 목록
print(AgentManager.list_agents())  # ['outgoing', 'incoming']
```

**예상 결과:**
```
[AgentManager] Creating instance of 'outgoing' agent...
<agent.outgoing.OutgoingAgent object at 0x...>
[AgentManager] Creating instance of 'incoming' agent...
<agent.incoming.IncomingAgent object at 0x...>
['outgoing', 'incoming']
```

### 2.2 Outgoing Agent 테스트

```python
from agent.agent_manager import AgentManager

agent = AgentManager.get_outgoing()

# 테스트 1: 계좌번호 감지
result = agent.analyze("이 계좌로 보내줘 123-45-67890")
print(f"위험도: {result.risk_level}")
print(f"이유: {result.reasons}")
print(f"시크릿 전송 추천: {result.is_secret_recommended}")

# 테스트 2: 일반 메시지
result = agent.analyze("오늘 점심 뭐 먹을래?")
print(f"위험도: {result.risk_level}")
```

**예상 결과:**
```
위험도: RiskLevel.MEDIUM
이유: ['계좌번호 패턴이 감지되었습니다.']
시크릿 전송 추천: True

위험도: RiskLevel.LOW
```

### 2.3 Incoming Agent 테스트

```python
from agent.agent_manager import AgentManager

agent = AgentManager.get_incoming()

# 테스트 1: 가족 사칭 + 급전 요구
result = agent.analyze("엄마 나야. 폰 고장났어. 급해서 돈 좀 보내줘")
print(f"위험도: {result.risk_level}")
print(f"이유: {result.reasons}")

# 테스트 2: 일반 메시지
result = agent.analyze("오늘 날씨 좋네")
print(f"위험도: {result.risk_level}")
```

**예상 결과:**
```
위험도: RiskLevel.CRITICAL
이유: ['가족 사칭 및 금전 요구 패턴이 감지되었습니다.']

위험도: RiskLevel.LOW
```

---

## 3. LLM 모델 테스트

### 3.1 LLMManager 테스트 (선택 사항)

> ⚠️ **주의**: Kanana Safeguard 8B 모델은 ~8GB 메모리를 사용합니다.
> 처음 로드 시 5-10분 소요될 수 있습니다.

```bash
cd backend
./venv/Scripts/python.exe ../test_kanana_safeguard.py
```

**예상 실행 시간:** 5-10분 (첫 실행 시)

**예상 결과:**
```
🛡️ Kanana Safeguard 모델 직접 테스트
[LLMManager] Loading safeguard model for the first time...
Kanana LLM (safeguard) initializing on cpu...
Loading checkpoint shards: 100%|██████████| 4/4
Kanana LLM (safeguard) Loaded Successfully!

[테스트 1] 가족 사칭 + 송금 요구
안전 여부: ⚠️ 위험
카테고리: UNSAFE-S4
```

### 3.2 LLM 없이 Rule-based만 테스트

```python
from agent.tools import analyze_incoming

# use_ai=False로 LLM 없이 테스트
result = analyze_incoming("엄마 나야. 돈 좀 보내줘", use_ai=False)
print(f"위험도: {result.risk_level}")
```

---

## 4. FastAPI 서버 테스트

### 4.1 서버 시작

```bash
cd backend
./venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

**예상 결과:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 4.2 헬스체크

**새 터미널 열기:**

```bash
cd backend
./venv/Scripts/python.exe -c "import requests; r = requests.get('http://127.0.0.1:8000/api/agents/health'); print(r.json())"
```

**예상 결과:**
```json
{
  "status": "healthy",
  "agents": {
    "outgoing": "ready",
    "incoming": "ready"
  },
  "message": "Kanana DualGuard Agents are operational"
}
```

### 4.3 API 엔드포인트 테스트

#### Outgoing Agent API

```bash
cd backend
./venv/Scripts/python.exe -c "
import requests
import json
response = requests.post(
    'http://127.0.0.1:8000/api/agents/analyze/outgoing',
    json={'text': '계좌번호 123-45-67890'}
)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
"
```

**예상 결과:**
```json
{
  "risk_level": "MEDIUM",
  "reasons": ["계좌번호 패턴이 감지되었습니다."],
  "recommended_action": "시크릿 전송 추천",
  "is_secret_recommended": true
}
```

#### Incoming Agent API

```bash
cd backend
./venv/Scripts/python.exe -c "
import requests
import json
response = requests.post(
    'http://127.0.0.1:8000/api/agents/analyze/incoming',
    json={'text': '엄마 나야. 급해서 돈 좀 보내줘'}
)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
"
```

**예상 결과:**
```json
{
  "risk_level": "CRITICAL",
  "reasons": ["가족 사칭 및 금전 요구 패턴이 감지되었습니다."],
  "recommended_action": "차단 및 경고",
  "is_secret_recommended": false
}
```

### 4.4 통합 테스트 스크립트 실행

```bash
cd backend
./venv/Scripts/python.exe ../test_api.py
```

**예상 결과:** 모든 테스트 케이스 통과 (✅)

---

## 5. Node.js 서버 테스트

### 5.1 서버 시작

```bash
cd frontend/KakaoTalk/server
npm start
```

**예상 결과:**
```
[nodemon] starting `ts-node ./src/web.ts`
info: listening on port 8001...
info: Connected to DB successfully.
```

### 5.2 서버 연결 확인

**새 터미널:**

```bash
curl http://localhost:8001/
# 또는
python -c "import requests; print(requests.get('http://localhost:8001/').status_code)"
```

**예상 결과:** `200` (또는 `404`는 정상 - 루트 엔드포인트가 없을 수 있음)

---

## 6. 통합 테스트

### 6.1 FastAPI + Node.js 통합 테스트

**사전 조건:**
- FastAPI 서버 실행 중 (포트 8000)
- Node.js 서버 실행 중 (포트 8001)

```bash
cd backend
./venv/Scripts/python.exe ../test_integration.py
```

**예상 결과:**
```
✅ 통합 테스트 완료!
============================================================
```

### 6.2 전체 시스템 테스트 체크리스트

- [ ] FastAPI 서버 정상 실행
- [ ] Node.js 서버 정상 실행
- [ ] Outgoing Agent API 정상 동작
- [ ] Incoming Agent API 정상 동작
- [ ] AgentManager를 통한 Agent 접근 정상
- [ ] LLMManager를 통한 LLM 로드 정상 (선택)
- [ ] Socket.io 연결 정상

---

## 7. 트러블슈팅

### 문제 1: 가상환경이 활성화되지 않음

**증상:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**해결:**
```bash
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 문제 2: 포트 충돌

**증상:**
```
Address already in use
```

**해결:**
```bash
# Windows에서 포트 사용 프로세스 확인
netstat -ano | findstr :8000
# PID 확인 후 종료
taskkill /PID <PID> /F

# 또는 다른 포트 사용
uvicorn app.main:app --port 8001
```

### 문제 3: Kanana Safeguard 모델 로드 실패

**증상:**
```
Failed to load Kanana LLM
Running in fallback mode (Rule-based only).
```

**원인:** 메모리 부족 또는 네트워크 문제

**해결:**
1. 충분한 메모리 확보 (최소 8GB)
2. 인터넷 연결 확인 (HuggingFace에서 다운로드)
3. Rule-based만 사용하는 것도 가능 (`use_ai=False`)

### 문제 4: AgentManager에서 Agent를 찾을 수 없음

**증상:**
```
[AgentManager] Agent 'xxx' not found in registry.
```

**해결:**
```python
# agent_manager.py 확인
print(AgentManager.list_agents())  # 등록된 Agent 목록 확인
```

### 문제 5: UTF-8 인코딩 오류 (Windows)

**증상:**
```
UnicodeEncodeError: 'cp949' codec can't encode character
```

**해결:**
테스트 스크립트에 다음 코드 추가:
```python
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

---

## 빠른 테스트 명령어 모음

```bash
# 1. 가상환경 활성화
cd backend && .\venv\Scripts\activate

# 2. Agent 단위 테스트 (Python 인터프리터)
python
>>> from agent.agent_manager import AgentManager
>>> AgentManager.get_outgoing().analyze("계좌번호 123-45-67890")

# 3. FastAPI 서버 시작
./venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# 4. 통합 테스트 실행 (새 터미널)
cd backend && ./venv/Scripts/python.exe ../test_integration.py

# 5. Node.js 서버 시작 (새 터미널)
cd frontend/KakaoTalk/server && npm start
```

---

## 테스트 성공 기준

### ✅ 최소 통과 기준
- [ ] FastAPI 서버 실행 성공
- [ ] `/api/agents/health` 응답 200
- [ ] Outgoing Agent 계좌번호 감지 성공
- [ ] Incoming Agent 가족 사칭 감지 성공

### ✅ 완전 통과 기준
- [ ] 위 최소 기준 모두 통과
- [ ] Node.js 서버 실행 성공
- [ ] test_integration.py 모든 테스트 통과
- [ ] Kanana Safeguard 모델 로드 성공 (선택)

---

## 다음 단계

테스트 통과 후:
1. [MAINTENANCE_GUIDE.md](./MAINTENANCE_GUIDE.md) - 유지보수 가이드 참조
2. 새 Agent 추가 또는 기존 Agent 수정
3. 프론트엔드 UI 통합
