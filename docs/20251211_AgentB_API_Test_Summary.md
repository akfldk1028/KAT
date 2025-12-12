# Agent B ver9.0.2 API 연결 및 파이프라인 테스트 요약

**작성일:** 2025-12-11
**버전:** ver9.0.2 3-Stage Pipeline (대화 맥락 분석 추가)
**최종 결과:** 9/9 PASS (100%)

---

## 0. ver9.0.2 주요 변경사항 (대화 맥락 기반 분석)

### 0.1 문제점 (ver9.0.1)
- 개별 메시지만 분석하여 멀티메시지 사기 패턴 감지 불가
- 예: "엄마 바빠?" → LOW, "90만원만 보내줘" → LOW (개별로는 무해)

### 0.2 해결책 (ver9.0.2)
- **conversation_history** 파라미터 추가로 이전 대화 맥락 전달
- **[상대방]/[나]** 구분으로 발신자 식별
- Stage 2 AI Agent가 전체 대화 흐름을 분석하여 사기 패턴 감지

### 0.3 수정된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `agent/agents/incoming.py` | `_stage2_ai_agent_categorization()`에 conversation_history, current_sender_id 파라미터 추가 |
| `agent/prompts/incoming_agent.py` | `STAGE2_AI_AGENT_PROMPT_WITH_CONTEXT` 템플릿 추가 |
| `backend/app/routers/agents.py` | `ConversationMessage` 모델 추가, API 엔드포인트 수정 |

### 0.4 API 요청 예시

```json
POST /api/agents/analyze/incoming
{
  "text": "엄마가 먼저 90만원만 보내주라",
  "sender_id": "123",
  "receiver_id": "456",
  "conversation_history": [
    {"sender_id": 123, "message": "엄마 바빠?", "timestamp": "2025-12-11T10:00:00"},
    {"sender_id": 456, "message": "응 왜?", "timestamp": "2025-12-11T10:01:00"},
    {"sender_id": 123, "message": "내가 급하게 친구한테 돈 보내줄 게 있는데", "timestamp": "2025-12-11T10:02:00"}
  ],
  "use_ai": true
}
```

### 0.5 테스트 결과 (A-004 대출 빙자 C-1)

```
[Stage 2] 분류: C-1 (대출 빙자), 신뢰도: 0.91
[Stage 3] 판정: DANGEROUS
[힌트] "이 메시지는 대출 빙자 사기일 수 있어요"
```

---

## 1. API 연결 상태

| API | 상태 | 비고 |
|-----|------|------|
| **TheCheat** | Mock DB | API Key 미설정 (테스트용 Mock 사용) |
| **LRL (URL Check)** | ERR_INVALID_KEY | API 키 확인 필요 (https://api.lrl.kr) |
| **KISA Phishing** | 연결됨 | 27,582건 캐시 (2025-12-10 갱신) |
| **VirusTotal** | 연결됨 | Rate limit 적용 (15초/요청) |
| **Kanana LLM** | 연결됨 | kanana-2-30b-a3b-instruct |
| **Grafana** | 실행중 | http://localhost:3001 |
| **Prometheus** | 실행중 | http://localhost:9090 |

---

## 2. 3-Stage 파이프라인 테스트 결과

**총 결과: 9/9 PASS (100%)**

| 테스트 | 유형 | 기대값 | 실제값 | 상태 | 시간(ms) |
|--------|------|--------|--------|------|----------|
| A-1 | 가족사칭 | HIGH | HIGH | PASS | 9086 |
| A-2 | 부고알림 | HIGH | HIGH | PASS | 14000 |
| B-1 | 검찰사칭 | HIGH | HIGH | PASS | 8896 |
| B-2 | 교통과태료 | HIGH | HIGH | PASS | 9822 |
| B-3 | 택배사기 | HIGH | HIGH | PASS | 14688 |
| C-1 | 대출사기 | HIGH | HIGH | PASS | 8506 |
| C-2 | 투자사기 | HIGH | HIGH | PASS | 8585 |
| NORMAL-1 | 일반대화 | LOW | LOW | PASS | 1376 |
| NORMAL-2 | 일상채팅 | LOW | LOW | PASS | 1166 |

**평균 응답 시간:** 8458ms

---

## 3. 수정된 코드

### 3.1 테스트 명명규칙 통일 (`test_agent_b_pipeline.py`)

```python
# Before: CRITICAL, HIGH_RISK, SUSPICIOUS, SAFE
# After: LOW, MEDIUM, HIGH, CRITICAL (RiskLevel enum 일치)

TEST_CASES = [
    {"expected": "HIGH"},    # 스미싱 유형
    {"expected": "LOW"},     # NORMAL
    {"expected": "CRITICAL"} # DB HIT
]
```

### 3.2 B카테고리 위험도 상향 (`incoming.py:_stage3_rule_fallback`)

```python
# Before: B-1, B-2, B-3 → SUSPICIOUS (고정)
# After: 모든 스미싱 유형 → DANGEROUS (고신뢰도 + 초면)

elif category in ["A-1", "A-2", "A-3", "B-1", "B-2", "B-3", "C-1", "C-2", "C-3"]:
    if confidence >= 0.7:
        if history_days < 7 or not is_saved_contact:
            risk_level = "DANGEROUS"  # 초면/미저장 → 위험
        else:
            risk_level = "SUSPICIOUS"  # 장기관계 → 주의
```

### 3.3 LRL API GET 방식 변경 (`lrl_api.py`)

```python
# Before: POST 방식
# After: GET 방식 (공식 문서 예제)

params = {"key": self.api_key, "url": url}
response = requests.get(self.endpoint, params=params, timeout=10)
```

---

## 4. LRL API 문제 (미해결)

**증상:**
```
[LRL] URL 검사 실패: → API 키 오류: ERR_INVALID_KEY (HTTP 403)
```

**API 키:** `9f7dc55c-797a-4e13-814c-e3135d808f04`

**해결 방법:**
1. https://lrl.kr 로그인
2. https://api.lrl.kr 에서 키 상태 확인
3. URL Check API v5 전용 키 활성화 또는 재발급

**참고:** LRL API 없이도 KISA(27,582건) + VirusTotal fallback으로 URL 위협 탐지 가능

---

## 5. 3-Stage Pipeline 동작 확인

```
[Stage 1] DB 블랙리스트: None (0ms)           → DB HIT면 CRITICAL 즉시 종료
[Stage 2] AI Agent 분류: B-2 (신뢰도: 0.95)   → 9개 유형 분류
[Stage 3] AI Judge 판정: DANGEROUS            → 최종 위험도 결정
```

- **Stage 2에서 NORMAL + 고신뢰도** → Stage 3 스킵, `LOW` 반환 (1.1-1.4초)
- **Stage 2에서 스미싱 유형** → Stage 3 AI Judge 판정 (8-14초)

---

## 6. 환경 설정

### .env 파일 (backend/.env)
```
KANANA_LLM_API_KEY=KC_IS_39DCHwz3U3Og...
KANANA_LLM_BASE_URL=https://kanana-2-30b-a3b-s7nyu.a2s-endpoint.kr-central-2.kakaocloud.com/v1
LRL_API_KEY=9f7dc55c-797a-4e13-814c-e3135d808f04  # 확인 필요
VIRUSTOTAL_API_KEY=565bac3c0908e263...
KISA_PHISHING_API_KEY=6e95a3a558604a0d...
```

### Docker 서비스
```bash
# 실행 중인 서비스
grafana:     localhost:3001 (admin/katadmin123)
prometheus:  localhost:9090
loki:        localhost:3100
```

---

## 7. 참고 문서

- [LRL.kr API 문서](https://lrl.kr/bbs/board.php?bo_table=docs&wr_id=27)
- [TheCheat API 문서](https://apidocs.thecheat.co.kr/docs/api-usage/api-search-guide/)
- Agent B ver9.0 기획서: `docs/20251210_AgentB_ver9.0_Final.md`

---

## 8. 멀티메시지 테스트 케이스 (26개)

테스트 케이스 파일: `docs/dev_test_sample.json`

| Case ID | 유형 | 설명 | 예상 분류 |
|---------|------|------|-----------|
| A-001 | 가족사칭 | 폰 인증 안되서 돈 보내달라 | A-1 |
| A-002 | 가족사칭 | 액정 깨져서 보험 신청 (앱 설치 유도) | A-1 |
| A-003 | 투자사기 | VIP 수익 인증, 급등주 정보 | C-2 |
| A-004 | 대출빙자 | 새희망홀씨 대출 승인, 전화 유도 | C-1 |
| A-005 | 택배사기 | 배송 지연, 주소지 재입력 | B-3 |
| B-006 | 가족사칭 | 폰 고장 PC카톡, 수리비 | A-1 |
| B-007 | 가족사칭 | 문상 구매 대리, 신분증/카드 요청 | A-1 |
| B-008 | 가족사칭 | 교수님 선물, 기프트카드 요청 | A-1 |
| B-009 | 지인사칭 | 직장동료 사칭, 폰 초기화 | A-3 |
| B-010 | 로맨스스캠 | 번호 잘못 저장, 친구 요청 | C-3 |
| A-011 | 기관사칭 | 개인정보 유출, 보호조치 해제 | B-1 |
| A-012 | 기관사칭 | 민생회복 소비쿠폰 지급 | B-2 |
| A-013 | 기관사칭 | 카드 배송, 명의도용 신고 | B-2 |
| A-014 | 기관사칭 | KISA 가상자산 피해구제 | B-1 |
| B-015 | 가족사칭 | SKT 해킹, 인증번호/비밀번호 요청 | A-1 |
| B-016 | 기관사칭 | 유심 복제 해킹, 보안 유심 배송 | B-2 |
| B-017 | 가족사칭 | 쿠팡 해킹, 카드번호 요청 | A-1 |
| A-018 | 부고알림 | 부고 링크 (악성 URL) | A-2 |
| A-019 | 청첩장 | 모바일 청첩장 링크 (악성 URL) | A-2 |
| A-020 | 검찰사칭 | 대포통장, 피의자 전환 협박 | B-1 |
| A-021 | 투자사기 | 쇼핑몰 리뷰 알바 | C-2 |
| A-022 | 기관사칭 | 건강보험 환급금 | B-2 |
| B-023 | 로맨스스캠 | 필라테스 강사 오인, 친구 요청 | C-3 |
| B-024 | 투자사기 | 손실 복구, 정보방 초대 | C-2 |
| B-025 | 중고거래 | 당근마켓 안전결제 피싱 | B-3 |
| B-026 | 기관사칭 | 해외직구 관세 미납, 명의도용 | B-2 |

### 테스트 스크립트 실행
```bash
cd D:\Data\18_KAT\KAT
python test_conversation_flow.py
```
