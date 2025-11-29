# DualGuard MCP Tools

MCP(Model Context Protocol) 도구 11개의 역할과 발동 조건을 정리한 문서입니다.

## 도구 분류 요약

| 카테고리 | 도구명 | 역할 | 발동 시점 |
|---------|--------|------|----------|
| **Agent 분석** | `analyze_outgoing` | 발신 메시지 민감정보 분석 | 메시지 전송 시 |
| | `analyze_incoming` | 수신 메시지 피싱/사기 탐지 | 메시지 수신 시 |
| | `analyze_image` | 이미지 OCR + 분석 | 이미지 전송 시 |
| **정보 조회** | `list_pii_patterns` | PII 패턴 목록 | LLM이 패턴 정보 필요 시 |
| | `list_document_types` | 문서 유형 목록 | 문서 식별 전 |
| | `get_risk_rules` | 조합 규칙 조회 | 위험도 계산 로직 확인 시 |
| **Core 분석** | `scan_pii` | 텍스트 PII 스캔 | 분석 1단계 |
| | `identify_document` | 문서 유형 식별 | OCR 텍스트 분석 시 |
| | `evaluate_risk` | 위험도 계산 | 분석 2단계 |
| | `get_action_for_risk` | 권장 조치 반환 | 분석 3단계 |
| | `analyze_full` | 전체 파이프라인 | 단일 호출로 전체 분석 |

---

## 1. Agent 기반 도구 (상위 레벨)

### 1.1 `analyze_outgoing`

**역할**: 발신 메시지의 민감정보(계좌번호, 주민번호 등)를 감지하고 보호 조치 제안

**발동 조건**:
- 사용자가 메시지 전송 버튼 클릭 시
- API 엔드포인트: `POST /api/agents/analyze/outgoing`

**입력**:
```json
{
  "text": "계좌번호 110-123-456789로 보내줘",
  "use_ai": true
}
```

**출력**:
```json
{
  "risk_level": "MEDIUM",
  "reasons": ["은행계좌번호 패턴이 감지되었습니다."],
  "recommended_action": "시크릿 전송 권장",
  "is_secret_recommended": true
}
```

**내부 흐름**:
```
use_ai=false: Rule-based 분석
  └─> scan_pii → evaluate_risk → get_action_for_risk

use_ai=true: LLM + MCP 분석
  └─> Kanana LLM → MCP Client → analyze_full 호출
                              → LLM이 결과 해석 후 응답
```

---

### 1.2 `analyze_incoming`

**역할**: 수신 메시지의 피싱/스미싱/보이스피싱 위협 탐지

**발동 조건**:
- 새 메시지 수신 시
- 의심스러운 링크/패턴 감지 시
- API 엔드포인트: `POST /api/agents/analyze/incoming`

**입력**:
```json
{
  "text": "[긴급] 계정이 정지됩니다. 지금 확인: bit.ly/xxx",
  "sender_id": "unknown_user",
  "use_ai": false
}
```

**출력**:
```json
{
  "risk_level": "HIGH",
  "reasons": ["피싱 의심 URL 패턴", "긴급성 유도 키워드"],
  "recommended_action": "주의 필요",
  "is_secret_recommended": false
}
```

---

### 1.3 `analyze_image`

**역할**: 이미지 내 텍스트 추출(OCR) 후 민감정보 분석

**발동 조건**:
- 이미지 파일 전송 시도 시
- 스크린샷 공유 시

**처리 흐름**:
```
이미지 입력
    ↓
[Step 1] Kanana Vision (3B) → OCR 텍스트 추출
    ↓
[Step 2] Vision 언로드 (GPU 메모리 해제)
    ↓
[Step 3] 추출된 텍스트 → analyze_outgoing 파이프라인
    ↓
분석 결과 반환
```

**입력**:
```json
{
  "image_path": "/path/to/screenshot.png",
  "use_ai": true
}
```

---

## 2. 정보 조회 도구 (Meta 정보)

### 2.1 `list_pii_patterns`

**역할**: 시스템이 감지할 수 있는 모든 PII 패턴 목록 반환

**발동 조건**:
- LLM이 "어떤 민감정보를 탐지할 수 있나요?" 질문 시
- 분석 전 감지 가능 범위 확인 시

**출력 예시**:
```json
{
  "financial": [
    {"id": "bank_account", "name_ko": "은행계좌번호", "risk_level": "MEDIUM"},
    {"id": "credit_card", "name_ko": "신용카드번호", "risk_level": "HIGH"}
  ],
  "government_id": [
    {"id": "resident_id", "name_ko": "주민등록번호", "risk_level": "CRITICAL"}
  ]
}
```

---

### 2.2 `list_document_types`

**역할**: 이미지에서 식별 가능한 문서 유형 목록 반환

**발동 조건**:
- 이미지 분석 전 문서 유형 확인 시
- LLM이 "어떤 문서를 인식하나요?" 질문 시

**출력 예시**:
```json
[
  {"id": "resident_card", "name_ko": "주민등록증", "risk_level": "CRITICAL"},
  {"id": "passport", "name_ko": "여권", "risk_level": "CRITICAL"},
  {"id": "driver_license", "name_ko": "운전면허증", "risk_level": "HIGH"}
]
```

---

### 2.3 `get_risk_rules`

**역할**: 위험도 상향 조합 규칙 반환

**발동 조건**:
- LLM이 위험도 계산 로직 확인 시
- "왜 위험도가 CRITICAL인가요?" 질문 시

**출력 예시**:
```json
{
  "combination_rules": [
    {
      "id": "identity_theft",
      "name_ko": "신원도용 위험",
      "requires": ["person_name", "resident_id"],
      "escalate_to": "CRITICAL"
    }
  ],
  "auto_escalation": {
    "count_threshold": 3,
    "escalate_to": "HIGH"
  }
}
```

---

## 3. Core 분석 도구 (실행 레벨)

### 3.1 `scan_pii`

**역할**: 정규식 패턴으로 텍스트에서 PII 스캔

**발동 조건**:
- 분석 파이프라인 1단계
- LLM이 "이 텍스트에서 PII를 찾아줘" 요청 시

**입력**:
```json
{"text": "주민번호 900101-1234567 입니다"}
```

**출력**:
```json
{
  "found_pii": [
    {
      "id": "resident_id",
      "category": "government_id",
      "value": "900101-1234567",
      "risk_level": "CRITICAL",
      "name_ko": "주민등록번호"
    }
  ],
  "categories_found": ["government_id"],
  "highest_risk": "CRITICAL",
  "count": 1
}
```

---

### 3.2 `identify_document`

**역할**: OCR 텍스트에서 문서 유형 식별

**발동 조건**:
- 이미지 분석 시 문서 종류 판별 필요
- Vision OCR 결과 분석 시

**입력**:
```json
{"ocr_text": "주민등록증 홍길동 900101-1234567 서울특별시..."}
```

**출력**:
```json
{
  "document_type": "resident_card",
  "name_ko": "주민등록증",
  "risk_level": "CRITICAL",
  "confidence": "high",
  "matched_keywords": 3
}
```

---

### 3.3 `evaluate_risk`

**역할**: 감지된 PII 목록으로 최종 위험도 계산

**발동 조건**:
- 분석 파이프라인 2단계
- scan_pii 결과 처리 후

**특징**:
- 조합 규칙 적용 (이름+주민번호 → CRITICAL)
- 개수 기반 상향 (3개 이상 → HIGH)

**입력**:
```json
{
  "detected_items": [
    {"id": "person_name", "risk_level": "LOW"},
    {"id": "resident_id", "risk_level": "CRITICAL"}
  ]
}
```

**출력**:
```json
{
  "final_risk": "CRITICAL",
  "base_risk": "CRITICAL",
  "escalation_reason": "신원도용 위험: 이름+주민번호 조합 감지",
  "is_secret_recommended": true,
  "matched_rules": ["identity_theft"],
  "detected_count": 2
}
```

---

### 3.4 `get_action_for_risk`

**역할**: 위험도에 따른 권장 조치 반환

**발동 조건**:
- 분석 파이프라인 3단계
- 최종 결과 생성 시

**입력/출력**:
| 입력 (risk_level) | 출력 (권장 조치) |
|-------------------|------------------|
| `LOW` | "전송" |
| `MEDIUM` | "시크릿 전송 권장" |
| `HIGH` | "시크릿 전송 강력 권장" |
| `CRITICAL` | "시크릿 전송 필수" |

---

### 3.5 `analyze_full`

**역할**: 전체 분석 파이프라인을 단일 호출로 실행

**발동 조건**:
- LLM이 한 번에 전체 분석 원할 때
- 빠른 분석 필요 시

**내부 흐름**:
```
analyze_full(text)
    ├─> scan_pii(text)           # 1단계: PII 스캔
    ├─> evaluate_risk(found_pii)  # 2단계: 위험도 계산
    ├─> get_action_for_risk(risk) # 3단계: 권장 조치
    └─> 요약 생성                  # 4단계: summary
```

**출력**:
```json
{
  "pii_scan": { ... },
  "risk_evaluation": { ... },
  "recommended_action": "시크릿 전송 필수",
  "summary": "2종의 민감정보 감지: 주민등록번호, 이름. 시크릿 전송 필수"
}
```

---

## 시나리오별 도구 체인

### 시나리오 1: 일반 텍스트 메시지 전송

```
사용자: "계좌번호 110-123-456789로 보내줘" [전송 클릭]
    ↓
[2-Tier 필터링]
    ├─ 숫자 패턴 있음? → YES
    ↓
[Rule-based 또는 AI 분석]
    ↓
analyze_outgoing(text, use_ai=true)
    ↓
Kanana LLM → analyze_full 도구 호출
    ↓
scan_pii → evaluate_risk → get_action_for_risk
    ↓
결과: MEDIUM, 시크릿 전송 권장
```

### 시나리오 2: 이미지 전송

```
사용자: 주민등록증 사진 첨부 [전송 클릭]
    ↓
analyze_image(image_path)
    ↓
[Step 1] Kanana Vision OCR
    └─ "주민등록증 홍길동 900101-1234567..."
    ↓
[Step 2] identify_document(ocr_text)
    └─ 문서 유형: 주민등록증 (CRITICAL)
    ↓
[Step 3] analyze_outgoing(ocr_text)
    ↓
결과: CRITICAL, 시크릿 전송 필수
```

### 시나리오 3: 의심스러운 메시지 수신

```
수신: "[긴급] 계정 정지됩니다. 확인: bit.ly/xxx"
    ↓
analyze_incoming(text, sender_id)
    ↓
피싱 패턴 분석
    ├─ 긴급성 키워드 감지
    ├─ 단축 URL 감지
    └─ 계정 관련 키워드 감지
    ↓
결과: HIGH, 피싱 의심 경고 표시
```

---

## 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                        사용자 인터페이스                      │
│  [메시지 입력] [이미지 첨부] [전송 버튼]                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Server (:8002)                   │
│  /api/agents/analyze/outgoing                                │
│  /api/agents/analyze/incoming                                │
│  /api/mcp/info                                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ Outgoing    │   │ Incoming    │   │ Vision      │
│ Agent       │   │ Agent       │   │ Agent       │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Kanana LLM (MCP Client)                   │
│                                                              │
│  analyze_with_mcp() ──────────────────────────────────────▶ │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              MCP Tool Calls                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │    │
│  │  │ scan_pii     │  │ evaluate_risk│  │analyze_full│ │    │
│  │  └──────────────┘  └──────────────┘  └───────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Pattern Matcher                           │
│  - sensitive_patterns.json                                   │
│  - 정규식 PII 감지                                           │
│  - 조합 규칙 적용                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 파일 위치

| 파일 | 역할 |
|------|------|
| `agent/mcp/tools.py` | MCP 도구 정의 (@mcp.tool 데코레이터) |
| `agent/mcp/client.py` | MCP 클라이언트 (LLM → 도구 호출) |
| `agent/core/pattern_matcher.py` | 핵심 분석 로직 |
| `agent/data/sensitive_patterns.json` | PII 패턴/조합 규칙 |
| `agent/agents/outgoing.py` | 발신 분석 Agent |
| `agent/agents/incoming.py` | 수신 분석 Agent |
| `agent/llm/kanana.py` | Kanana LLM 관리자 |
