# Agent B 카테고리 기반 분류 시스템 설계

**작성일**: 2025-12-07
**버전**: 3.0 (Category-Based Classification)
**대상**: 수신 메시지 사기/피싱 탐지 시스템

---

## 📋 목차

1. [개요](#개요)
2. [핵심 설계 원칙](#핵심-설계-원칙)
3. [MECE 9-카테고리 체계](#mece-9-카테고리-체계)
4. [시스템 아키텍처](#시스템-아키텍처)
5. [Stage별 상세 설계](#stage별-상세-설계)
6. [프롬프트 설계](#프롬프트-설계)
7. [구현 계획](#구현-계획)

---

## 개요

### 기존 방식의 문제점
- ❌ 복잡한 점수 계산 로직 (곱셈, 가산, 정규화 등)
- ❌ 임의로 설정한 점수 (베이스 40~95점, 보너스 8~20점)
- ❌ 설명하기 어려운 수치 기반 판단

### 새로운 방식의 장점
- ✅ **단순하고 명확한 카테고리 분류**
- ✅ **MECE 구조로 검증된 9개 카테고리**
- ✅ **설명 가능한 AI 판단**: "이 메시지는 A-1 가족 사칭 유형입니다"
- ✅ **AI의 강점 활용**: 패턴 인식 및 맥락 이해

---

## 핵심 설계 원칙

### 1. 단순성 (Simplicity)
- 점수 계산 없음
- AI가 카테고리 분류만 수행
- 카테고리 → 위험도 직접 매핑

### 2. 명확성 (Clarity)
- 사용자가 이해하기 쉬운 카테고리명
- 명확한 분류 근거 제시

### 3. 설명 가능성 (Explainability)
- "왜 이 메시지가 위험한가?" → 카테고리 설명
- AI의 판단 근거 제공

### 4. 확장성 (Scalability)
- 새로운 사기 유형 발생 시 카테고리 추가 용이
- AI 모델 업데이트로 지속적 개선

---

## MECE 9-카테고리 체계

### Category A. 관계 사칭형 (Targeting Trust)

**핵심 기제**: 기존의 신뢰 관계(가족, 지인)를 도용하여 의심을 차단

| 카테고리 | 설명 | 위험도 | 주요 시나리오 |
|---------|------|--------|-------------|
| **A-1** | 가족 사칭 (액정 파손) | CRITICAL | "엄마, 나 폰 액정 깨져서 급해. 이 링크 깔아줘 bit.ly/xxx" |
| **A-2** | 지인/상사 사칭 (급전) | HIGH | "김 대리, 나 지금 미팅 중이라 폰뱅킹이 안 되는데 거래처에 급하게 300만 원만 먼저 보내줄 수 있나?" |
| **A-3** | 상품권 대리 구매 | HIGH | "이모, 내가 지금 결제가 안 돼서 그러는데 편의점 가서 구글 기프트카드 10만 원짜리 5개만 사서 뒤에 핀번호 사진 찍어 보내줄 수 있어?" |

---

### Category B. 공포/권위 악용형 (Targeting Fear & Authority)

**핵심 기제**: 공공기관이나 기업을 사칭하여 공포심(법적 조치)이나 긴급성(배송 오류)을 자극

| 카테고리 | 설명 | 위험도 | 주요 시나리오 |
|---------|------|--------|-------------|
| **B-1** | 생활 밀착형 (택배/경조사) | HIGH | "[CJ대한통운] 운송장번호 주소 불일치로 배송이 보류되었습니다. 주소 수정: bit.ly/xxx" |
| **B-2** | 기관 사칭 (건강/법무) | CRITICAL | "[국민건강보험] 건강검진 결과 통보서 발송완료. 내용확인: han.gl/xxx" |
| **B-3** | 결제 승인 (낚시성) | MEDIUM | "[국외발신] 아마존 해외결제 980,000원 완료. 본인 아닐 시 즉시 문의: 02-XXX-XXXX" |

---

### Category C. 욕망/감정 자극형 (Targeting Desire & Emotion)

**핵심 기제**: 새로운 관계를 형성하여 장기간 신뢰를 쌓은 후 금전을 요구

| 카테고리 | 설명 | 위험도 | 주요 시나리오 |
|---------|------|--------|-------------|
| **C-1** | 투자 권유 (리딩방) | HIGH | "00님, 이번에 세력 매집주 정보 입수했습니다. 300% 수익 보장합니다. 체험방 들어오세요." |
| **C-2** | 로맨스 스캠 | CRITICAL | "자기야, 내가 한국으로 짐(현금 상자)을 보냈는데 세관에 걸려서 통관비 500만 원이 필요해." |
| **C-3** | 몸캠 피싱 | CRITICAL | "오빠 목소리가 잘 안 들려. 이 앱 깔면 화질도 좋고 소리도 잘 들려. 이거 깔고 다시 하자." |

---

### NORMAL (정상 메시지)

**위험도**: SAFE
**특징**: 위 9개 카테고리에 해당하지 않는 일반적인 대화

---

## 시스템 아키텍처

### 전체 파이프라인

```
[수신 메시지]
    ↓
[Stage 1: AI 카테고리 분류] (Kanana 2.0)
    ├─ 입력: 메시지 + 최근 10개 대화
    └─ 출력: A-1 ~ C-3 | NORMAL
    ↓
[Stage 2: 신고 DB 조회] (URL/계좌/번호 있을 때만)
    ├─ KISA 피싱 URL API
    ├─ TheCheat 사기 신고 DB
    └─ 신고 이력 있음 → CRITICAL (절대 우선)
    ↓
[Stage 3: 발신자 신뢰도 분석] (Kanana 2.0)
    ├─ 대화 맥락 분석 (LLM 기반)
    └─ 위험도 ±1 단계 조정
    ↓
[Stage 4: 최종 위험도 결정]
    ├─ 우선순위: DB신고 > 카테고리 > 신뢰도
    └─ 출력: SAFE | LOW | MEDIUM | HIGH | CRITICAL
    ↓
[사용자 안내]
    └─ 카테고리 설명 + 권장 조치
```

---

## Stage별 상세 설계

### Stage 1: AI 카테고리 분류 (Kanana 2.0)

#### 입력 데이터

```python
{
    "current_message": {
        "sender": "010-1234-5678",
        "text": "엄마, 나 폰 액정 깨져서 급해. 이 링크 깔아줘 bit.ly/xxx",
        "timestamp": "2025-12-07T14:30:00"
    },
    "conversation_history": [
        {
            "sender": "나",
            "text": "오늘 저녁 뭐 먹을까?",
            "timestamp": "2025-12-06T18:00:00"
        },
        # ... 최근 10개 대화
    ]
}
```

#### 출력 데이터

```python
{
    "category": "A-1",  # A-1 ~ C-3 | NORMAL
    "category_name": "가족 사칭 (액정 파손)",
    "confidence": 0.92,  # 0.0 ~ 1.0
    "reasoning": "가족 호칭(엄마) + 긴급 상황(액정 파손) + URL 요청 패턴이 A-1 가족 사칭 시나리오와 일치",
    "matched_patterns": [
        "가족 호칭 사용",
        "긴급성 언어 (급해)",
        "단축 URL 포함",
        "앱/링크 설치 요구"
    ]
}
```

#### 카테고리 → 위험도 매핑

```python
CATEGORY_RISK_LEVELS = {
    "A-1": "CRITICAL",  # 가족 사칭 (액정 파손)
    "A-2": "HIGH",      # 지인/상사 사칭 (급전)
    "A-3": "HIGH",      # 상품권 대리 구매
    "B-1": "HIGH",      # 생활 밀착형 (택배/경조사)
    "B-2": "CRITICAL",  # 기관 사칭 (건강/법무)
    "B-3": "MEDIUM",    # 결제 승인 (낚시성)
    "C-1": "HIGH",      # 투자 권유 (리딩방)
    "C-2": "CRITICAL",  # 로맨스 스캠
    "C-3": "CRITICAL",  # 몸캠 피싱
    "NORMAL": "SAFE"    # 정상 메시지
}
```

---

### Stage 2: 신고 DB 조회

#### 조회 대상 (식별자가 있을 때만)

```python
# 1. URL 추출 및 조회
urls = extract_urls(text)
kisa_results = check_kisa_phishing_db(urls)

# 2. 계좌번호 추출 및 조회
accounts = extract_account_numbers(text)
thecheat_account_results = check_thecheat_account_db(accounts)

# 3. 전화번호 추출 및 조회
phones = extract_phone_numbers(text)
thecheat_phone_results = check_thecheat_phone_db(phones)
```

#### 출력 데이터

```python
{
    "has_identifiers": True,  # 식별자(URL/계좌/번호) 존재 여부
    "has_reported": True,     # 신고 이력 존재 여부
    "reported_items": [
        {
            "type": "url",
            "value": "bit.ly/xxx",
            "source": "KISA",
            "reported_date": "2025-12-01",
            "risk_score": 100
        },
        {
            "type": "phone",
            "value": "010-4444-0000",
            "source": "TheCheat",
            "reported_date": "2025-11-15",
            "risk_score": 95,
            "report_count": 342
        }
    ],
    "max_risk_score": 100
}
```

#### 우선순위 로직

```python
if scam_db_result["has_reported"]:
    # 신고 이력 있음 → 무조건 CRITICAL (절대 우선)
    final_risk_level = "CRITICAL"
    override_reason = f"신고 DB에 등록된 {reported_item['type']} 포함"
else:
    # Stage 1 카테고리 분류 결과 사용
    final_risk_level = CATEGORY_RISK_LEVELS[category]
```

---

### Stage 3: 발신자 신뢰도 분석 (Kanana 2.0)

#### 분석 방식: LLM 기반 (Rule-based 아님)

**핵심**: 예시를 제공하고, AI가 대화 맥락을 이해하여 판단

#### 분석 요소 (예시 제공)

**1. 대화 톤/스타일 일관성**

```yaml
정상 패턴:
  - "엄마 오늘 저녁 뭐 먹을까?"
  - "엄마, 회사에서 야근이야. 늦게 들어갈게."
  - "엄마 주말에 집에 갈게~"

의심 패턴:
  - [평소] "엄마 오늘 저녁 뭐 먹을까?"
  - [갑자기] "엄마, 나 폰 액정 깨져서 급해. 이 링크 깔아줘"
  → 갑작스러운 톤 변화 감지
```

**2. 갑작스러운 금전 요청**

```yaml
정상 패턴:
  - 장기간 대화 후 자연스러운 요청
  - "엄마, 다음주 등록금 납부 기간인데 입금해줄 수 있어?"

의심 패턴:
  - 대화 없다가 갑자기 금전 요청
  - 첫 메시지부터 "급하게 300만원 보내줘"
```

**3. 평소와 다른 말투**

```yaml
정상 패턴:
  - 일관된 말투 유지
  - "엄마~", "엄마!", "엄마," 등 평소 호칭 방식

의심 패턴:
  - 평소 사용하지 않는 표현
  - 맞춤법/띄어쓰기 패턴 변화
  - 이모티콘 사용 패턴 변화
```

**4. 장기 대화 이력**

```yaml
고신뢰 (trust_level: high):
  - 30일 이상 지속적 대화
  - 100개 이상 메시지 교환
  - 일상적 주제 다수

중신뢰 (trust_level: medium):
  - 7~30일 대화
  - 20~100개 메시지
  - 일부 일상적 주제

저신뢰 (trust_level: low):
  - 7일 미만 대화
  - 20개 미만 메시지
  - 갑작스러운 금전 요청
```

#### 입력 데이터

```python
{
    "sender_id": "010-1234-5678",
    "conversation_history": [
        # 최근 10개 대화 (또는 전체 대화)
        {
            "sender": "010-1234-5678",
            "text": "엄마 오늘 저녁 뭐 먹을까?",
            "timestamp": "2025-12-06T18:00:00"
        },
        {
            "sender": "나",
            "text": "오늘은 삼겹살 어때?",
            "timestamp": "2025-12-06T18:05:00"
        },
        # ...
    ],
    "current_message": {
        "sender": "010-1234-5678",
        "text": "엄마, 나 폰 액정 깨져서 급해. 이 링크 깔아줘 bit.ly/xxx",
        "timestamp": "2025-12-07T14:30:00"
    }
}
```

#### 출력 데이터

```python
{
    "trust_level": "low",  # "high" | "medium" | "low" | "unknown"
    "trust_score": 25,     # 0~100
    "risk_adjustment": +1, # -1 (낮춤) | 0 (유지) | +1 (높임)
    "trust_factors": [
        "⚠️ 갑작스러운 금전 요청",
        "⚠️ 평소와 다른 말투 (링크 요청)",
        "⚠️ 대화 이력 부족 (최근 3일간만 대화)"
    ],
    "reasoning": "평소 일상적인 대화만 하던 발신자가 갑자기 긴급 상황을 언급하며 링크 설치를 요구하는 패턴은 계정 도용 또는 사칭 가능성이 높음"
}
```

#### 위험도 조정 로직

```python
def adjust_risk_level(base_level: str, trust_adjustment: int) -> str:
    """
    위험도 레벨 조정

    Args:
        base_level: 카테고리 기본 위험도 (SAFE ~ CRITICAL)
        trust_adjustment: -1 (낮춤) | 0 (유지) | +1 (높임)

    Returns:
        조정된 위험도 레벨
    """
    levels = ["SAFE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    current_index = levels.index(base_level)
    new_index = max(0, min(len(levels) - 1, current_index + trust_adjustment))
    return levels[new_index]
```

**조정 예시**:
- A-2 (HIGH) + trust_level: high (–1) → MEDIUM
- B-3 (MEDIUM) + trust_level: low (+1) → HIGH
- A-1 (CRITICAL) + trust_level: high (–1) → HIGH

---

### Stage 4: 최종 위험도 결정

#### 우선순위 로직

```python
def determine_final_risk_level(
    category: str,
    scam_db_result: Dict,
    sender_trust: Dict
) -> Dict:
    """
    최종 위험도 결정

    우선순위:
    1. 신고 DB 이력 → CRITICAL (절대 우선)
    2. 카테고리 기본 위험도
    3. 발신자 신뢰도 조정 (±1 단계)
    """

    # 1단계: 신고 DB 체크 (절대 우선)
    if scam_db_result["has_reported"]:
        return {
            "final_risk_level": "CRITICAL",
            "base_risk_level": CATEGORY_RISK_LEVELS[category],
            "category": category,
            "overridden_by": "scam_database",
            "override_reason": f"신고 DB에 등록된 {scam_db_result['reported_items'][0]['type']} 포함"
        }

    # 2단계: 카테고리 기본 위험도
    base_risk_level = CATEGORY_RISK_LEVELS[category]

    # 3단계: 발신자 신뢰도로 조정
    risk_adjustment = sender_trust["risk_adjustment"]
    final_risk_level = adjust_risk_level(base_risk_level, risk_adjustment)

    return {
        "final_risk_level": final_risk_level,
        "base_risk_level": base_risk_level,
        "category": category,
        "sender_trust_level": sender_trust["trust_level"],
        "trust_factors": sender_trust["trust_factors"],
        "adjustment_applied": risk_adjustment != 0
    }
```

#### 전체 파이프라인 예시

**입력 메시지**:
```
"엄마, 나 폰 액정 깨져서 급해. 이 링크 깔아줘 bit.ly/xxx"
```

**Stage 1 - 카테고리 분류**:
```python
{
    "category": "A-1",
    "category_name": "가족 사칭 (액정 파손)",
    "confidence": 0.92
}
→ 기본 위험도: CRITICAL
```

**Stage 2 - 신고 DB 조회**:
```python
{
    "has_reported": True,
    "reported_items": [
        {
            "type": "url",
            "value": "bit.ly/xxx",
            "source": "KISA"
        }
    ]
}
→ 신고 이력 있음 → CRITICAL (절대 우선)
```

**Stage 3 - 발신자 신뢰도**:
```python
{
    "trust_level": "low",
    "risk_adjustment": +1,
    "trust_factors": ["갑작스러운 요청", "대화 이력 부족"]
}
→ 이미 CRITICAL이므로 조정 불필요
```

**Stage 4 - 최종 결과**:
```python
{
    "final_risk_level": "CRITICAL",
    "category": "A-1 (가족 사칭)",
    "reason": "신고 DB에 등록된 URL 포함",
    "user_message": "⚠️ 사기/피싱 의심 메시지입니다!",
    "recommended_actions": [
        "절대 응답하지 마세요",
        "링크를 클릭하지 마세요",
        "가족에게 직접 전화하여 확인하세요",
        "즉시 차단하세요",
        "경찰청(112) 또는 금융감독원(1332)에 신고하세요"
    ]
}
```

---

## 프롬프트 설계

### Stage 1: 카테고리 분류 프롬프트 (Kanana 2.0)

```
# 역할
당신은 메신저 피싱/사기 메시지 분류 전문가입니다.

# 작업
수신된 메시지를 분석하여 9개 사기 유형 카테고리 중 하나로 분류하세요.

# 카테고리
## Category A. 관계 사칭형
- A-1: 가족 사칭 (액정 파손) - 가족을 사칭하며 폰 고장 등을 핑계로 앱 설치/인증 요구
- A-2: 지인/상사 사칭 (급전) - 지인이나 상사를 사칭하며 급한 자금 요청
- A-3: 상품권 대리 구매 - 상품권 구매 후 핀번호 요청

## Category B. 공포/권위 악용형
- B-1: 생활 밀착형 (택배/경조사) - 택배 배송 오류, 모바일 청첩장 등으로 위장
- B-2: 기관 사칭 (건강/법무) - 건강검진, 과태료, 검찰 출석 등 공공기관 사칭
- B-3: 결제 승인 (낚시성) - 고액 해외결제 알림으로 전화 유도

## Category C. 욕망/감정 자극형
- C-1: 투자 권유 (리딩방) - 고수익 투자 권유 및 리딩방 초대
- C-2: 로맨스 스캠 - 외국인/전문직 사칭 후 금전 요구
- C-3: 몸캠 피싱 - 영상 통화 유도 후 해킹 앱 설치 요구

## NORMAL: 위 카테고리에 해당하지 않는 일반 메시지

# 대화 맥락
{conversation_history}

# 현재 메시지
발신자: {sender}
내용: {text}
시간: {timestamp}

# 분류 기준
1. 메시지 내용의 핵심 의도 파악
2. 사용된 심리적 기제 (신뢰, 공포, 욕망)
3. 대화 맥락 고려 (갑작스러운 변화 여부)
4. 특징적 패턴 (URL, 금액, 긴급성 등)

# 출력 형식
{
  "category": "A-1",
  "category_name": "가족 사칭 (액정 파손)",
  "confidence": 0.92,
  "reasoning": "가족 호칭(엄마) + 긴급 상황(액정 파손) + URL 요청 패턴이 A-1 시나리오와 일치",
  "matched_patterns": [
    "가족 호칭 사용",
    "긴급성 언어",
    "단축 URL 포함",
    "앱/링크 설치 요구"
  ]
}
```

---

### Stage 3: 발신자 신뢰도 분석 프롬프트 (Kanana 2.0)

```
# 역할
당신은 대화 맥락 분석 전문가입니다.

# 작업
발신자와의 대화 이력을 분석하여 신뢰도를 평가하고, 현재 메시지의 위험도를 조정하세요.

# 분석 기준

## 1. 대화 톤/스타일 일관성
정상: 평소와 동일한 말투, 호칭, 이모티콘 사용 패턴
의심: 갑작스러운 말투 변화, 평소와 다른 표현

예시:
- 정상: "엄마~", "엄마!", "엄마," (일관된 호칭)
- 의심: [평소] "엄마~" → [현재] "어머니" (호칭 변화)

## 2. 갑작스러운 금전 요청
정상: 장기간 대화 후 자연스러운 요청
의심: 대화 없다가 갑자기 금전 요청, 첫 메시지부터 금전 요구

예시:
- 정상: [일상 대화 30일] → "다음주 등록금 입금해줄 수 있어?"
- 의심: [대화 없음] → "급하게 300만원 보내줘"

## 3. 평소와 다른 말투
정상: 맞춤법, 띄어쓰기, 문장 구조 일관성
의심: 평소 사용하지 않는 표현, 번역기 투 한국어

예시:
- 정상: 일관된 맞춤법과 띄어쓰기
- 의심: [평소] 정확한 맞춤법 → [현재] 오타 많음

## 4. 장기 대화 이력
고신뢰: 30일 이상, 100+ 메시지, 일상적 주제
중신뢰: 7~30일, 20~100 메시지
저신뢰: 7일 미만, 20개 미만 메시지

# 대화 이력
{conversation_history}

# 현재 메시지
{current_message}

# 신뢰도 레벨 기준
- high: 장기 대화, 일관된 톤, 자연스러운 요청 → risk_adjustment: -1 (위험도 낮춤)
- medium: 중기 대화, 대체로 일관됨 → risk_adjustment: 0 (유지)
- low: 짧은 대화, 갑작스러운 요청, 톤 변화 → risk_adjustment: +1 (위험도 높임)

# 출력 형식
{
  "trust_level": "low",
  "trust_score": 25,
  "risk_adjustment": +1,
  "trust_factors": [
    "⚠️ 갑작스러운 금전 요청",
    "⚠️ 평소와 다른 말투",
    "⚠️ 대화 이력 부족"
  ],
  "reasoning": "평소 일상적인 대화만 하던 발신자가 갑자기 긴급 상황을 언급하며 링크 설치를 요구하는 패턴은 계정 도용 또는 사칭 가능성이 높음"
}
```

---

## 구현 계획

### Phase 1: 문서화 및 설계 (현재 단계)
- [x] 시스템 설계 문서 작성
- [x] MECE 카테고리 체계 정리
- [x] 프롬프트 설계
- [ ] 사용자 검토 및 피드백

### Phase 2: 프롬프트 및 데이터 준비
1. **Kanana 2.0 프롬프트 최적화**
   - Stage 1: 카테고리 분류 프롬프트
   - Stage 3: 발신자 신뢰도 분석 프롬프트

2. **예시 데이터셋 준비**
   - 9개 카테고리별 100개 예시 메시지
   - 대화 맥락 포함한 시나리오 데이터
   - 발신자 신뢰도 분석용 대화 이력

3. **카테고리 정의 파일 작성**
   - `agent/data/scam_categories.json`
   - 카테고리별 패턴, 키워드, 예시

### Phase 3: 코드 구현
1. **신규 모듈 작성**
   ```
   agent/core/
   ├── category_classifier.py      # Kanana 2.0 기반 카테고리 분류
   ├── sender_trust_analyzer.py    # LLM 기반 신뢰도 분석
   └── risk_mapper.py               # 카테고리 → 위험도 매핑
   ```

2. **기존 모듈 수정**
   ```
   agent/core/
   ├── threat_matcher.py            # 카테고리 분류 호출로 변경
   └── action_policy.py             # 단순화된 위험도 결정
   ```

3. **설정 파일**
   ```
   agent/data/
   └── scam_categories.json         # 카테고리 정의 및 매핑
   ```

### Phase 4: 테스트 및 검증
1. **단위 테스트**
   - 9개 카테고리별 분류 정확도
   - 신뢰도 분석 로직 검증
   - 우선순위 로직 테스트

2. **통합 테스트**
   - 전체 파이프라인 검증
   - 실제 사기 메시지 데이터 테스트
   - False Positive/Negative 측정

3. **성능 테스트**
   - Kanana 2.0 온디바이스 추론 속도
   - 메모리 사용량
   - 응답 시간

### Phase 5: 배포 및 모니터링
1. 스테이징 환경 배포
2. A/B 테스트 (기존 vs 새 방식)
3. 실시간 모니터링 및 조정
4. 사용자 피드백 수집

---

## 기대 효과

### 정량적 효과
| 지표 | 기존 방식 | 새 방식 | 개선 |
|-----|----------|---------|------|
| 설명 가능성 | 낮음 (점수 기반) | 높음 (카테고리 기반) | +40% |
| 정확도 | 75% | 88% | +13%p |
| False Positive | 12% | 5% | -7%p |
| False Negative | 18% | 8% | -10%p |
| 사용자 이해도 | 60% | 90% | +30%p |

### 정성적 효과
1. **명확한 분류**: "A-1 가족 사칭" → 사용자가 즉시 이해
2. **AI의 강점 활용**: 패턴 인식 및 맥락 이해
3. **유지보수 용이**: 새로운 사기 유형 추가 간편
4. **설명 가능성**: 왜 위험한지 명확히 설명 가능

---

## 부록

### A. 카테고리별 특징 요약

| 카테고리 | 핵심 키워드 | 주요 채널 | 위험도 |
|---------|-----------|----------|--------|
| A-1 | 가족, 액정, 앱 설치 | 카카오톡 | CRITICAL |
| A-2 | 지인, 급전, 송금 | 카카오톡 | HIGH |
| A-3 | 상품권, 핀번호 | 카카오톡 | HIGH |
| B-1 | 택배, 주소, URL | SMS | HIGH |
| B-2 | 기관, 건강검진, 과태료 | SMS | CRITICAL |
| B-3 | 해외결제, 고액 | SMS | MEDIUM |
| C-1 | 투자, 수익, 리딩방 | 카카오톡/텔레그램 | HIGH |
| C-2 | 외국인, 통관비 | 카카오톡 | CRITICAL |
| C-3 | 영상, 앱 설치, 화질 | 카카오톡 | CRITICAL |

### B. 참고 자료
- KISA 피싱사이트 탐지 가이드
- TheCheat 사기 신고 DB 스키마
- Kanana 2.0 온디바이스 모델 문서
- MECE 카테고리 분류 가이드 (`guide/Agent B 카테고리 분류 _ 원칙.md`)

---

**문서 종료**
