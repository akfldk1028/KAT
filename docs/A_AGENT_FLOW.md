# A Agent (안심 전송) - 전체 Flow

## 개요
발신 메시지에서 민감한 개인정보(PII)를 감지하고 시크릿 전송을 권장하는 보안 에이전트

---

## 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         A Agent (안심 전송) Flow                              │
└─────────────────────────────────────────────────────────────────────────────┘

[사용자가 채팅창에서 메시지 전송 버튼 클릭]
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 프론트엔드 (ChattingRoomContainer.tsx)                                       │
│                                                                             │
│   onChatSubmit(msg) 호출                                                    │
│        │                                                                    │
│        ▼                                                                    │
│   handleTextAnalysis(msg) ──────────────────────────────────────────────┐  │
│        │                                                                │  │
│        │  axios.post('http://localhost:8002/api/agents/analyze/outgoing')  │
│        │  { text: "계좌번호 110-123-456789", use_ai: false }            │  │
│        │                                                                │  │
└────────┼────────────────────────────────────────────────────────────────┼──┘
         │                                                                │
         ▼                                                                │
┌─────────────────────────────────────────────────────────────────────────────┐
│ 백엔드 API (server.py:8002)                                                  │
│                                                                             │
│   @app.post("/api/agents/analyze/outgoing")                                 │
│   async def api_analyze_outgoing(request):                                  │
│        │                                                                    │
│        ▼                                                                    │
│   analyze_outgoing(text, use_ai) ← MCP Tool 호출                           │
│                                                                             │
└────────┼────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Agent Layer (outgoing.py)                                                    │
│                                                                             │
│   OutgoingAgent.analyze(text, use_ai)                                       │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────┐                                  │
│   │ Tier 1: 빠른 필터링 (~0ms)           │                                  │
│   │ _has_suspicious_pattern(text)       │                                  │
│   │                                     │                                  │
│   │ - 숫자 8자리+ 연속 패턴?             │                                  │
│   │ - 키워드 (계좌, 카드, 주민 등)?      │                                  │
│   └─────────────────────────────────────┘                                  │
│        │                                                                    │
│   ┌────┴────┐                                                              │
│   │         │                                                              │
│   ▼         ▼                                                              │
│ [없음]    [있음]                                                            │
│   │         │                                                              │
│   ▼         ▼                                                              │
│ LOW 반환  ┌─────────────────────────────────────┐                          │
│ (바로통과) │ Tier 2: 정밀 분석                   │                          │
│           │                                     │                          │
│           │  use_ai=false → Rule-based 분석     │                          │
│           │  use_ai=true  → Kanana LLM + ReAct  │                          │
│           └─────────────────────────────────────┘                          │
│                    │                                                        │
│                    ▼                                                        │
│           AnalysisResponse {                                                │
│             risk_level: "MEDIUM",                                          │
│             reasons: ["계좌번호 패턴이 감지되었습니다."],                      │
│             is_secret_recommended: true                                     │
│           }                                                                 │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 프론트엔드 분기 처리                                                          │
│                                                                             │
│   if (risk_level !== 'LOW' && is_secret_recommended) {                      │
│       // SecurityAlert 팝업 표시                                             │
│       setState({ securityAnalysis: response, isTextAnalysis: true });       │
│       return false;  // 전송 중단                                            │
│   } else {                                                                  │
│       return true;   // 바로 전송                                            │
│   }                                                                         │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ SecurityAlert 컴포넌트 (민감정보 감지 시)                                      │
│                                                                             │
│   ┌────────────────────────────────────────────┐                           │
│   │  ⚠️ 주의 필요                               │                           │
│   │                                            │                           │
│   │  • 계좌번호 패턴이 감지되었습니다.           │                           │
│   │                                            │                           │
│   │  권장 조치: 시크릿 전송 추천                 │                           │
│   │                                            │                           │
│   │  ┌──────────┐    ┌──────────┐              │                           │
│   │  │   취소   │    │   전송   │              │                           │
│   │  └──────────┘    └──────────┘              │                           │
│   └────────────────────────────────────────────┘                           │
│                                                                             │
│   [취소] → clearAnalysisState() → 메시지 전송 안됨                           │
│   [전송] → handleTextConfirm() → sendTextMessage(msg) → socket.emit()       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 이미지 분석 Flow

```
[이미지 선택] ─────────────────────────────────────────────────────────────────┐
      │                                                                        │
      ▼                                                                        │
┌─────────────────────────────────────────────────────────────────────────────┐
│ handleImageSelect(file)                                                      │
│      │                                                                       │
│      ├─ 미리보기 생성 (FileReader)                                            │
│      │                                                                       │
│      └─ analyzeImage(file) ─────────────────────────────────────────────────>│
│              │                                                               │
│              │  POST /api/agents/analyze/image                               │
│              │  FormData: file                                               │
│              │                                                               │
└──────────────┼───────────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 백엔드 (server.py)                                                           │
│                                                                             │
│   analyze_image(temp_path, use_ai)                                          │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────┐                                  │
│   │ Step 1: Kanana Vision OCR           │                                  │
│   │ 이미지에서 텍스트 추출               │                                  │
│   │ LLMManager.get("vision")            │                                  │
│   └─────────────────────────────────────┘                                  │
│        │                                                                    │
│        ▼                                                                    │
│   extracted_text = "계좌번호 110-123-456789"                                │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────┐                                  │
│   │ Step 2: 텍스트 분석                  │                                  │
│   │ analyze_outgoing(extracted_text)    │                                  │
│   │ (동일한 2-Tier 분석)                 │                                  │
│   └─────────────────────────────────────┘                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 감지 가능한 민감정보 (PII)

| 유형 | 패턴 예시 | 위험도 |
|------|----------|--------|
| 주민등록번호 | 900101-1234567 | CRITICAL |
| 외국인등록번호 | 900101-5234567 | CRITICAL |
| 여권번호 | M12345678 | CRITICAL |
| 신용카드번호 | 1234-5678-9012-3456 | HIGH |
| 운전면허번호 | 11-22-123456-78 | HIGH |
| 계좌번호 | 110-123-456789 | MEDIUM |
| 전화번호 | 010-1234-5678 | LOW |

---

## 파일 구조

```
frontend/KakaoTalk/client/src/
├── apis/
│   └── agent.ts                    # API 호출 함수
│       ├── analyzeOutgoing()       # 텍스트 분석
│       ├── analyzeImage()          # 이미지 분석
│       └── checkAgentHealth()      # 서버 상태 확인
│
├── constants.ts
│   └── AGENT_HOST                  # http://localhost:8002/api/agents
│
├── containers/chattingRoom/
│   └── ChattingRoomContainer.tsx   # 메인 컨테이너
│       ├── handleTextAnalysis()    # 텍스트 분석 호출
│       ├── handleImageSelect()     # 이미지 분석 호출
│       ├── handleTextConfirm()     # 텍스트 전송 확인
│       └── handleSecurityConfirm() # 이미지 전송 확인
│
└── components/chattingRoom/
    └── SecurityAlert/              # 경고 UI
        ├── index.tsx               # 메인 컴포넌트
        ├── AlertBox.tsx            # 경고 박스
        ├── RiskBadge.tsx           # 위험도 뱃지
        └── ActionButtons.tsx       # 버튼

backend/api/
└── server.py                       # FastAPI (포트 8002)
    ├── /api/agents/health          # 헬스체크
    ├── /api/agents/analyze/outgoing # 텍스트 분석
    ├── /api/agents/analyze/image   # 이미지 분석
    └── /api/agents/ocr             # OCR만 수행

agent/
├── mcp/
│   └── tools.py                    # MCP 도구 정의
│       ├── analyze_outgoing()
│       ├── analyze_incoming()
│       └── analyze_image()
│
├── agents/
│   └── outgoing.py                 # OutgoingAgent
│       ├── analyze()               # 2-Tier 분석
│       ├── _has_suspicious_pattern() # Tier 1
│       ├── _analyze_rule_based()   # Tier 2 (기본)
│       └── _analyze_with_ai()      # Tier 2 (LLM)
│
├── prompts/
│   └── outgoing_agent.py           # ReAct 프롬프트
│
└── llm/
    └── kanana.py                   # LLMManager
        ├── get("instruct")         # Kanana Instruct 8B
        ├── get("vision")           # Kanana Vision 3B
        └── sequential_mode         # 순차 모드 (GPU 절약)
```

---

## API 엔드포인트

### 1. 텍스트 분석
```http
POST /api/agents/analyze/outgoing
Content-Type: application/json

{
  "text": "계좌번호 110-123-456789로 보내줘",
  "use_ai": false
}

Response:
{
  "risk_level": "MEDIUM",
  "reasons": ["계좌번호 패턴이 감지되었습니다."],
  "recommended_action": "시크릿 전송 추천",
  "is_secret_recommended": true
}
```

### 2. 이미지 분석
```http
POST /api/agents/analyze/image
Content-Type: multipart/form-data

file: (이미지 파일)
use_ai: false

Response:
{
  "risk_level": "MEDIUM",
  "reasons": ["계좌번호 패턴이 감지되었습니다."],
  "recommended_action": "시크릿 전송 추천",
  "is_secret_recommended": true
}
```

### 3. 헬스체크
```http
GET /api/agents/health

Response:
{
  "status": "ok",
  "service": "DualGuard Agent API"
}
```

---

## 성능

| 메시지 종류 | 처리 시간 | 설명 |
|------------|----------|------|
| 일반 텍스트 ("안녕") | ~0ms | Tier 1에서 바로 통과 |
| 민감정보 (Rule-based) | ~100ms | Tier 2 정규식 분석 |
| 민감정보 (LLM) | ~1-3초 | Kanana Instruct ReAct |
| 이미지 (OCR + 분석) | ~3-8초 | Vision + 텍스트 분석 |

---

## 2-Tier 분석 상세

### Tier 1: 빠른 필터링
```python
def _has_suspicious_pattern(self, text: str) -> bool:
    # 숫자가 8자리 이상 연속 (하이픈 포함)
    if re.search(r'[\d-]{8,}', text):
        return True

    # 민감정보 관련 키워드
    sensitive_keywords = [
        '계좌', '통장', '카드', '번호',
        '주민', '등록', '여권', '면허',
        '외국인', '비밀번호', '인증',
        '송금', '이체', '입금'
    ]
    for keyword in sensitive_keywords:
        if keyword in text:
            return True

    return False
```

### Tier 2: 정밀 분석

**Rule-based (기본)**
- 정규식 패턴 매칭
- 각 PII 유형별 위험도 판단
- ~100ms

**LLM (use_ai=true)**
- Kanana Instruct 8B
- ReAct 패턴 (Thought → Action → Observation → Answer)
- MCP 도구 호출 (detect_pii)
- ~1-3초

---

## 모델 사용

| 모델 | 용도 | 크기 |
|------|------|------|
| Kanana Instruct | 텍스트 분석 (ReAct) | 8B |
| Kanana Vision | 이미지 OCR | 3B |

**순차 모드**: GPU 메모리 제한으로 한 번에 하나의 모델만 로드

---

## 상태 관리 (프론트엔드)

```typescript
interface State {
  // 이미지 분석
  selectedImage: File | null;
  imagePreview: string | null;
  securityAnalysis: SecurityAnalysis | null;
  isAnalyzing: boolean;

  // 텍스트 분석
  pendingTextMessage: string | null;
  isTextAnalysis: boolean;
}
```

---

## 구현 완료 항목

- [x] 2-Tier 분석 로직 (빠른 필터링 + 정밀 분석)
- [x] Rule-based PII 감지
- [x] Kanana LLM + ReAct 패턴
- [x] 이미지 OCR (Kanana Vision)
- [x] FastAPI 엔드포인트
- [x] 프론트엔드 API 연동
- [x] SecurityAlert UI 컴포넌트
- [x] 텍스트/이미지 전송 전 분석
