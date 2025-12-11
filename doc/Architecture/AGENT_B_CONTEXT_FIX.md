# Agent B (Incoming Guard) - 대화 맥락 전달 수정 사항

## Agent B의 목적 (중요!)

Agent B는 **사기를 "탐지"하는 것이 아니라**, 사용자에게 **"그럴 가능성이 있다"**는 것을 알려주는 역할.

- 대화 전체적인 맥락을 보고 MECE 카테고리에 해당하는 패턴을 감지하면 경고
- 확정적 판단이 아닌 **가능성 기반 경고 시스템**
- 사용자가 스스로 판단할 수 있도록 정보 제공

### MECE 카테고리
| 코드 | 카테고리 | 예시 |
|------|----------|------|
| A | 관계 사칭 | 가족(엄마/아빠/자녀), 지인, 친구 |
| B | 공포/권위 | 경찰, 금감원, 법원, 체납, 영장 |
| C | 욕구/감정 | 로맨스 스캠, 투자 사기, 당첨 |

---

## 순차적 흐름 분석 (Frontend → Node.js → Python)

### 1단계: Frontend (React)

**파일**: `frontend/KakaoTalk/client/src/services/agentService.ts`

```
사용자가 메시지 수신
    ↓
ChatBlock.tsx에서 analyzeIncoming() 호출
    ↓
agentService.ts가 API 요청 생성:
{
  text: "엄마 나 폰 액정 깨졌어",
  sender_id: 1,        // 발신자 ID
  receiver_id: 2,      // 수신자(현재 사용자) ID
  use_ai: true
}
    ↓
POST http://localhost:8003/api/agents/analyze/incoming
```

**현재 상태**: sender_id, receiver_id 모두 전달 (정상)

---

### 2단계: Node.js Backend

**파일**: `frontend/KakaoTalk/server/src/`

```
Frontend의 API 요청
    ↓
Node.js는 현재 Proxy 역할만 수행
(채팅 히스토리 접근 가능하지만 전달 안함)
    ↓
Python API로 그대로 전달
```

**현재 상태**: 채팅 히스토리 있지만 미사용 (향후 개선 가능)

---

### 3단계: Python Backend (FastAPI)

**파일**: `backend/api/server.py` (Line 203-233)

```python
@app.post("/api/agents/analyze/incoming", response_model=AnalysisResponse)
async def api_analyze_incoming(request: IncomingRequest):
    sender_id = str(request.sender_id) if request.sender_id else None
    user_id = str(request.receiver_id) if request.receiver_id else None  # 수정됨!

    result = analyze_incoming(
        request.text,
        sender_id=sender_id,
        user_id=user_id,      # 수정됨!
        use_ai=request.use_ai
    )
```

**수정 내용**: `receiver_id`를 `user_id`로 변환하여 전달

---

### 4단계: MCP Tools

**파일**: `agent/mcp/tools.py` (Line 72-86)

```python
@mcp.tool()
def analyze_incoming(text: str, sender_id: str = None, user_id: str = None, use_ai: bool = False):
    agent = _get_incoming_agent()
    return agent.analyze(text, sender_id=sender_id, user_id=user_id, use_ai=use_ai)
```

**수정 내용**: `user_id` 파라미터 추가

---

### 5단계: IncomingAgent (4단계 분석 파이프라인)

**파일**: `agent/agents/incoming.py` (Line 103-109)

```python
# Stage 3: 발신자 신뢰도 분석
if user_id and sender_id:
    print(f"[IncomingAgent] Stage 3: 발신자 신뢰도 분석 (user={user_id}, sender={sender_id})...")
    stage3 = analyze_sender_risk(user_id, sender_id, text)
else:
    print("[IncomingAgent] Stage 3: 스킵 (user_id/sender_id 없음)")
```

---

## 수정 전후 비교

### 수정 전
```
Frontend → Node.js → Python API → IncomingAgent
                     receiver_id 받음    user_id=None → Stage 3 스킵!
```

### 수정 후
```
Frontend → Node.js → Python API → IncomingAgent
                     receiver_id → user_id 변환 → Stage 3 활성화!
```

---

## IncomingAgent 4단계 분석 파이프라인

| Stage | 이름 | 조건 | 상태 |
|-------|------|------|------|
| 1 | 텍스트 패턴 분석 (MECE) | 항상 | 작동 |
| 2 | 사기 신고 DB 조회 | 항상 | 작동 |
| 3 | 발신자 신뢰도 분석 | user_id && sender_id | **수정됨** |
| 4 | 정책 기반 최종 판정 | 항상 | 작동 |

---

## 관련 파일 전체 목록

### Frontend (React)
- `frontend/KakaoTalk/client/src/services/agentService.ts`: API 호출
- `frontend/KakaoTalk/client/src/components/chattingRoom/ChatBlock.tsx`: 메시지 표시
- `frontend/KakaoTalk/client/src/constants.ts`: API 엔드포인트 설정

### Node.js Backend
- `frontend/KakaoTalk/server/src/`: 프록시 역할

### Python Backend
- `backend/api/server.py`: FastAPI 엔드포인트 (수정됨)
- `agent/mcp/tools.py`: MCP 도구 인터페이스 (수정됨)
- `agent/agents/incoming.py`: IncomingAgent 클래스 (4단계 분석)
- `agent/core/conversation_analyzer.py`: 발신자 신뢰도 계산
- `agent/core/threat_matcher.py`: MECE 카테고리 매칭
- `agent/data/threat_patterns.json`: 위협 패턴 정의

---

## 테스트 방법

### API 테스트 (sender_id=1, receiver_id=2)
```bash
curl -X POST http://localhost:8003/api/agents/analyze/incoming \
  -H "Content-Type: application/json" \
  -d '{"text": "엄마 나 폰 액정 깨졌어 돈 좀 보내줘", "sender_id": 1, "receiver_id": 2, "use_ai": true}'
```

### 서버 로그 확인
```
[IncomingAgent] Stage 3: 발신자 신뢰도 분석 (user=2, sender=1)...
```

Stage 3이 실행되면 수정 성공!

---

## 포트 정보

| 포트 | 서비스 | 상태 |
|------|--------|------|
| 3000 | React Frontend | 사용 |
| 8001 | Node.js Backend | 사용 |
| 8002 | 좀비 소켓 | Windows 재부팅 필요 |
| 8003 | Python FastAPI (Agent API) | **사용** |

---

## 향후 개선 사항: 전체 대화 히스토리 전달

현재는 **단일 메시지 + user_id/sender_id**만 분석.
향후 **전체 대화 히스토리**를 전달하면 더 정확한 맥락 분석 가능:

### 구현 방안

1. **Node.js에서 채팅 히스토리 조회**
   ```javascript
   // GET /api/chat/room/:roomId
   const history = await getChatHistory(roomId);
   ```

2. **Python API에 conversation_history 파라미터 추가**
   ```python
   class IncomingRequest(BaseModel):
       text: str
       sender_id: Optional[int] = None
       receiver_id: Optional[int] = None
       conversation_history: Optional[List[Dict]] = None  # 추가
       use_ai: bool = False
   ```

3. **IncomingAgent에서 전체 대화 맥락 분석**
   ```python
   def analyze(self, text, sender_id, user_id, conversation_history=None):
       # 최근 N개 메시지의 패턴 분석
       # 점진적 신뢰 구축 vs 갑작스러운 금전 요청 감지
   ```

---

## 알려진 이슈

### Windows 좀비 소켓 (포트 8002)
- **원인**: uvicorn 프로세스 종료 후에도 TCP 소켓이 커널에 남아있음
- **해결**: Windows 재부팅 또는 포트 8003 사용 (현재 적용)

### PowerShell UTF-8 인코딩
- **원인**: PowerShell의 Set-Content가 한글을 깨뜨림
- **해결**: Python 스크립트로 파일 수정
```python
python -c "
with open('file.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace(old, new)
with open('file.py', 'w', encoding='utf-8') as f:
    f.write(content)
"
```

---

## 요약

1. **문제**: Stage 3 (발신자 신뢰도 분석)이 항상 스킵됨
2. **원인**: `receiver_id`가 `user_id`로 변환되지 않음
3. **해결**: `server.py`와 `tools.py` 수정하여 파라미터 전달
4. **결과**: Stage 3 활성화, 발신자 신뢰도 분석 가능

---

작성일: 2025-12-04
최종 수정: 2025-12-04
