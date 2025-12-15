# Agent B 통합 아키텍처 설계서
## 안심 가드 AGENT - MCP 기반 카테고리 분류 시스템

**작성일**: 2025-12-07
**버전**: 4.0 (Integrated Architecture)
**대상**: 메신저 피싱/사기 탐지 및 능동적 개입 시스템
**기반**: AIagent_20251117_V0.7.pdf 기획서 + 사용자 제안 카테고리 분류 방식

---

## 📋 목차

1. [설계 철학](#설계-철학)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [6단계 처리 파이프라인](#6단계-처리-파이프라인)
4. [MECE 9-카테고리 체계](#mece-9-카테고리-체계)
5. [MCP 서버 상세 설계](#mcp-서버-상세-설계)
6. [Kanana 2.0 LLM 통합](#kanana-20-llm-통합)
7. [구현 계획](#구현-계획)
8. [부록](#부록)

---

## 설계 철학

### 핵심 원칙

#### 1. 단순성 (Simplicity)
- ❌ 복잡한 점수 계산 로직 제거
- ✅ MECE 9-카테고리 분류로 단순화
- ✅ AI가 카테고리 분류 → 위험도 직접 매핑

#### 2. 설명 가능성 (Explainability)
- "왜 위험한가?" → "A-1 가족 사칭 유형입니다"
- 카테고리별 구체적인 시나리오 제시
- AI 판단 근거 명확히 제공

#### 3. MCP 아키텍처 기반
- 6개 전문 MCP 서버로 역할 분산
- 각 단계별 독립적 검증 가능
- 확장성과 유지보수성 확보

#### 4. On-Device AI 우선
- Kanana 2.0 온디바이스 모델 활용
- 개인정보 보호 (Privacy by Design)
- 실시간 분석 및 즉각 대응

---

## 시스템 아키텍처

### 전체 구조도

```
┌─────────────────────────────────────────────────────────────┐
│                      사용자 채팅방 진입                         │
│                  (최근 10개 대화 컨텍스트 로드)                   │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ ① 맥락 분석 (Context Analyzer MCP)                            │
│    - Kanana 2.0: 대화 흐름 및 의도 추론                         │
│    - 출력: 9-카테고리 분류 (A-1 ~ C-3 | NORMAL)                │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ ② 정보 추출 (Entity Extractor MCP)                            │
│    - NER: URL, 계좌번호, 전화번호 추출                           │
│    - 출력: 식별자 리스트 (identifiers)                          │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ ③ 교차 검증 (Threat Intelligence MCP)                         │
│    - KISA 피싱 URL DB 조회                                     │
│    - TheCheat 사기 신고 DB 조회                                │
│    - 출력: 신고 이력 (has_reported: true/false)                │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ ④ 관계 분석 (Social Graph MCP)                                │
│    - Kanana 2.0: 발신자 신뢰도 분석                             │
│    - 대화 이력, 톤 변화, 갑작스러운 요청 감지                      │
│    - 출력: trust_level (high/medium/low), risk_adjustment      │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ ⑤ 종합 판단 (Decision Engine MCP)                             │
│    - 우선순위: DB신고 > 카테고리 > 신뢰도                         │
│    - 출력: SAFE | LOW | MEDIUM | HIGH | CRITICAL               │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ ⑥ 능동적 개입 (AI Agent 실행)                                  │
│    - CRITICAL/HIGH: 경고 팝업 + 차단 권장                       │
│    - MEDIUM: 주의 알림                                         │
│    - Privacy MCP: 개인정보 자동 검열                            │
│    - Verification MCP: 사용자 확인 프로세스                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 6단계 처리 파이프라인

### ① 맥락 분석 (Context Analyzer MCP)

**목적**: 대화 맥락을 이해하고 사기 유형 카테고리 분류

**담당 AI**: Kanana 2.0 on-device LLM

**입력 데이터**:
```python
{
    "conversation_context": [
        # 사용자가 채팅방 진입 시 최근 10개 대화
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
        # ... (최근 10개)
    ],
    "current_message": {
        "sender": "010-1234-5678",
        "text": "엄마, 나 폰 액정 깨져서 급해. 이 링크 깔아줘 bit.ly/xxx",
        "timestamp": "2025-12-07T14:30:00"
    }
}
```

**처리 프로세스**:
1. Kanana 2.0에 카테고리 분류 프롬프트 제공
2. 대화 맥락과 현재 메시지 종합 분석
3. 9개 사기 유형 카테고리 또는 NORMAL 분류
4. 판단 근거 및 매칭 패턴 제시

**출력 데이터**:
```python
{
    "category": "A-1",  # A-1 ~ C-3 | NORMAL
    "category_name": "가족 사칭 (액정 파손)",
    "confidence": 0.92,
    "reasoning": "가족 호칭(엄마) + 긴급 상황(액정 파손) + URL 요청 패턴이 A-1 시나리오와 일치",
    "matched_patterns": [
        "가족 호칭 사용",
        "긴급성 언어 (급해)",
        "단축 URL 포함 (bit.ly)",
        "앱/링크 설치 요구"
    ],
    "context_anomalies": [
        "평소 일상 대화 → 갑작스러운 긴급 요청",
        "이전 대화에서 URL 요청 이력 없음"
    ]
}
```

**카테고리 → 기본 위험도 매핑**:
```python
CATEGORY_BASE_RISK = {
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

### ② 정보 추출 (Entity Extractor MCP)

**목적**: 메시지에서 식별 가능한 위협 요소 추출

**기술 스택**: NER (Named Entity Recognition) + 정규식

**추출 대상**:
- **URL**: 단축 URL, 피싱 사이트, 악성 링크
- **계좌번호**: 은행 계좌, 가상계좌
- **전화번호**: 발신번호, 문의 번호
- **금액**: 요청 금액, 송금액
- **시간**: 마감 시간, 긴급성 표현

**처리 프로세스**:
```python
def extract_entities(message: str) -> Dict:
    """
    메시지에서 위협 식별자 추출
    """
    entities = {
        "urls": extract_urls(message),
        "accounts": extract_account_numbers(message),
        "phones": extract_phone_numbers(message),
        "amounts": extract_money_amounts(message),
        "urgency_keywords": extract_urgency_keywords(message)
    }

    # URL 정규화 (단축 URL 확장)
    entities["urls_expanded"] = expand_shortened_urls(entities["urls"])

    return entities
```

**출력 데이터**:
```python
{
    "has_identifiers": True,
    "urls": ["bit.ly/xxx"],
    "urls_expanded": ["http://malicious-site.com/phishing"],
    "accounts": [],
    "phones": [],
    "amounts": [],
    "urgency_keywords": ["급해", "긴급"]
}
```

**Stage ②와 ③의 관계**:
- 식별자가 **있는 경우**: Stage ③ 교차 검증 수행
- 식별자가 **없는 경우**: Stage ③ 건너뛰고 Stage ④로 진행

---

### ③ 교차 검증 (Threat Intelligence MCP)

**목적**: 외부 신고 DB와 교차 검증

**실행 조건**: Stage ②에서 식별자(URL/계좌/번호) 추출된 경우만

**외부 API 연동**:

#### 1. KISA 피싱 URL DB
```python
async def check_kisa_phishing_db(urls: List[str]) -> List[Dict]:
    """
    KISA 피싱사이트 탐지 API 조회
    """
    results = []
    for url in urls:
        response = await kisa_api.check_url(url)
        if response["is_phishing"]:
            results.append({
                "type": "url",
                "value": url,
                "source": "KISA",
                "reported_date": response["reported_date"],
                "risk_score": 100
            })
    return results
```

#### 2. TheCheat 사기 신고 DB
```python
async def check_thecheat_db(
    accounts: List[str],
    phones: List[str]
) -> List[Dict]:
    """
    TheCheat 계좌번호/전화번호 신고 조회
    """
    results = []

    # 계좌번호 조회
    for account in accounts:
        response = await thecheat_api.check_account(account)
        if response["is_reported"]:
            results.append({
                "type": "account",
                "value": account,
                "source": "TheCheat",
                "reported_date": response["reported_date"],
                "risk_score": 95,
                "report_count": response["count"]
            })

    # 전화번호 조회
    for phone in phones:
        response = await thecheat_api.check_phone(phone)
        if response["is_reported"]:
            results.append({
                "type": "phone",
                "value": phone,
                "source": "TheCheat",
                "reported_date": response["reported_date"],
                "risk_score": 90,
                "report_count": response["count"]
            })

    return results
```

**출력 데이터**:
```python
{
    "has_reported": True,  # 신고 이력 존재 여부
    "reported_items": [
        {
            "type": "url",
            "value": "bit.ly/xxx → http://malicious-site.com/phishing",
            "source": "KISA",
            "reported_date": "2025-12-01",
            "risk_score": 100
        }
    ],
    "max_risk_score": 100,
    "recommendation": "BLOCK_IMMEDIATELY"
}
```

**절대 우선순위 규칙**:
```python
if threat_intelligence_result["has_reported"]:
    # 신고 DB에 등록된 경우 무조건 CRITICAL
    # Stage ①의 카테고리 분류 결과 무시
    # Stage ④의 신뢰도 조정 무시
    final_risk_level = "CRITICAL"
    override_reason = f"신고 DB 등록 ({reported_item['source']})"
```

---

### ④ 관계 분석 (Social Graph MCP)

**목적**: 발신자와의 관계 및 대화 이력 분석

**담당 AI**: Kanana 2.0 on-device LLM

**분석 방식**: Rule-based ❌ → LLM 기반 예시 학습 ✅

**입력 데이터**:
```python
{
    "sender_id": "010-1234-5678",
    "conversation_history": [
        # 전체 대화 이력 또는 최근 30일
        {
            "sender": "010-1234-5678",
            "text": "엄마 오늘 저녁 뭐 먹을까?",
            "timestamp": "2025-12-06T18:00:00"
        },
        # ... (장기 대화 이력)
    ],
    "current_message": {
        "sender": "010-1234-5678",
        "text": "엄마, 나 폰 액정 깨져서 급해. 이 링크 깔아줘 bit.ly/xxx",
        "timestamp": "2025-12-07T14:30:00"
    },
    "sender_metadata": {
        "first_contact_date": "2023-01-15",
        "total_messages": 1247,
        "conversation_days": 692
    }
}
```

**분석 기준 (예시 기반 학습)**:

#### 1. 대화 톤/스타일 일관성
```yaml
정상 패턴 예시:
  - "엄마~", "엄마!", "엄마," (일관된 호칭)
  - 맞춤법/띄어쓰기 일관성
  - 이모티콘 사용 패턴 유지

의심 패턴 예시:
  - [평소] "엄마~" → [현재] "어머니" (호칭 변화)
  - [평소] 정확한 맞춤법 → [현재] 오타 많음
  - [평소] ㅋㅋ 사용 → [현재] ㅎㅎ 사용
```

#### 2. 갑작스러운 금전/행동 요청
```yaml
정상 패턴 예시:
  - 장기 대화 후 자연스러운 요청
  - "다음주 등록금 납부 기간인데 입금해줄 수 있어?"

의심 패턴 예시:
  - 대화 없다가 갑자기 금전 요청
  - 첫 메시지부터 "급하게 300만원 보내줘"
  - 링크 설치, 앱 다운로드 요구
```

#### 3. 평소와 다른 말투
```yaml
정상 패턴 예시:
  - 일관된 문장 구조
  - 평소 사용하는 표현 반복

의심 패턴 예시:
  - 번역기 투 한국어 (외국인 사칭)
  - 지나치게 격식적/비격식적
  - 평소 사용하지 않는 이모티콘/줄임말
```

#### 4. 장기 대화 이력
```yaml
고신뢰 (high):
  - 30일 이상 지속적 대화
  - 100+ 메시지 교환
  - 일상적 주제 다수
  → risk_adjustment: -1 (위험도 낮춤)

중신뢰 (medium):
  - 7~30일 대화
  - 20~100 메시지
  → risk_adjustment: 0 (유지)

저신뢰 (low):
  - 7일 미만 대화
  - 20개 미만 메시지
  - 갑작스러운 금전 요청
  → risk_adjustment: +1 (위험도 높임)
```

**처리 프로세스**:
```python
async def analyze_sender_trust(
    sender_id: str,
    conversation_history: List[Dict],
    current_message: Dict
) -> Dict:
    """
    Kanana 2.0 기반 발신자 신뢰도 분석
    """
    # Kanana 2.0 프롬프트 구성
    prompt = build_trust_analysis_prompt(
        conversation_history=conversation_history,
        current_message=current_message
    )

    # LLM 추론
    response = await kanana_llm.infer(prompt)

    # 신뢰도 레벨 및 조정값 계산
    trust_result = parse_trust_analysis(response)

    return trust_result
```

**출력 데이터**:
```python
{
    "trust_level": "low",  # "high" | "medium" | "low" | "unknown"
    "trust_score": 25,     # 0~100
    "risk_adjustment": +1, # -1 (낮춤) | 0 (유지) | +1 (높임)
    "trust_factors": [
        "⚠️ 갑작스러운 금전 요청",
        "⚠️ 평소와 다른 말투 (링크 요청)",
        "⚠️ 대화 이력 부족 (최근 3일간만 대화)",
        "⚠️ 톤 변화 감지 (일상 대화 → 긴급 요청)"
    ],
    "reasoning": "평소 일상적인 대화만 하던 발신자가 갑자기 긴급 상황을 언급하며 링크 설치를 요구하는 패턴은 계정 도용 또는 사칭 가능성이 높음",
    "conversation_metadata": {
        "total_days": 3,
        "total_messages": 8,
        "tone_consistency_score": 0.45,
        "request_pattern_abnormal": True
    }
}
```

---

### ⑤ 종합 판단 (Decision Engine MCP)

**목적**: 모든 분석 결과를 종합하여 최종 위험도 결정

**우선순위 로직**:
```
1순위: 신고 DB 이력 (Stage ③)
2순위: 카테고리 기본 위험도 (Stage ①)
3순위: 발신자 신뢰도 조정 (Stage ④)
```

**처리 프로세스**:
```python
def determine_final_risk(
    category_result: Dict,      # Stage ①
    entity_result: Dict,         # Stage ②
    threat_intel_result: Dict,   # Stage ③
    sender_trust_result: Dict    # Stage ④
) -> Dict:
    """
    최종 위험도 결정
    """

    # 1순위: 신고 DB 이력 체크
    if threat_intel_result["has_reported"]:
        return {
            "final_risk_level": "CRITICAL",
            "base_risk_level": CATEGORY_BASE_RISK[category_result["category"]],
            "category": category_result["category"],
            "category_name": category_result["category_name"],
            "overridden_by": "scam_database",
            "override_reason": f"신고 DB 등록 ({threat_intel_result['reported_items'][0]['source']})",
            "reported_items": threat_intel_result["reported_items"],
            "sender_trust": sender_trust_result,
            "recommendation": "BLOCK_IMMEDIATELY"
        }

    # 2순위: 카테고리 기본 위험도
    base_risk_level = CATEGORY_BASE_RISK[category_result["category"]]

    # 3순위: 발신자 신뢰도 조정
    risk_adjustment = sender_trust_result["risk_adjustment"]
    final_risk_level = adjust_risk_level(base_risk_level, risk_adjustment)

    return {
        "final_risk_level": final_risk_level,
        "base_risk_level": base_risk_level,
        "category": category_result["category"],
        "category_name": category_result["category_name"],
        "confidence": category_result["confidence"],
        "matched_patterns": category_result["matched_patterns"],
        "sender_trust_level": sender_trust_result["trust_level"],
        "trust_factors": sender_trust_result["trust_factors"],
        "adjustment_applied": risk_adjustment != 0,
        "recommendation": get_recommendation(final_risk_level)
    }


def adjust_risk_level(base_level: str, adjustment: int) -> str:
    """
    위험도 레벨 조정

    Args:
        base_level: SAFE | LOW | MEDIUM | HIGH | CRITICAL
        adjustment: -1 (낮춤) | 0 (유지) | +1 (높임)

    Returns:
        조정된 위험도 레벨
    """
    levels = ["SAFE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    current_index = levels.index(base_level)
    new_index = max(0, min(len(levels) - 1, current_index + adjustment))
    return levels[new_index]
```

**최종 출력 데이터**:
```python
{
    "final_risk_level": "CRITICAL",
    "base_risk_level": "CRITICAL",
    "category": "A-1",
    "category_name": "가족 사칭 (액정 파손)",
    "confidence": 0.92,
    "matched_patterns": [
        "가족 호칭 사용",
        "긴급성 언어",
        "단축 URL 포함",
        "앱/링크 설치 요구"
    ],
    "overridden_by": "scam_database",
    "override_reason": "신고 DB 등록 (KISA)",
    "reported_items": [
        {
            "type": "url",
            "value": "bit.ly/xxx",
            "source": "KISA"
        }
    ],
    "sender_trust_level": "low",
    "trust_factors": [
        "⚠️ 갑작스러운 금전 요청",
        "⚠️ 대화 이력 부족"
    ],
    "recommendation": "BLOCK_IMMEDIATELY"
}
```

---

### ⑥ 능동적 개입 (AI Agent 실행)

**목적**: 위험도에 따른 능동적 사용자 보호 조치

**개입 수준**:

#### CRITICAL (치명적 위험)
```python
{
    "intervention_level": "CRITICAL",
    "actions": [
        "❗ 전체 화면 경고 팝업 표시",
        "🚫 메시지 내용 자동 가림 (Privacy MCP)",
        "🔒 URL/계좌번호 클릭 차단",
        "📞 즉시 차단 권장",
        "🚨 신고 버튼 노출",
        "📋 경찰청(112), 금융감독원(1332) 연락처 제공"
    ],
    "user_message": "⚠️ 사기/피싱 의심 메시지입니다!",
    "explanation": "이 메시지는 '가족 사칭 (액정 파손)' 유형으로 분류되었으며, KISA 신고 DB에 등록된 피싱 URL이 포함되어 있습니다.",
    "recommended_actions": [
        "절대 응답하지 마세요",
        "링크를 클릭하지 마세요",
        "가족에게 직접 전화하여 확인하세요",
        "즉시 차단하세요",
        "경찰청(112) 또는 금융감독원(1332)에 신고하세요"
    ]
}
```

**Privacy MCP 연동**:
```python
async def apply_privacy_protection(message: Dict, risk_level: str) -> Dict:
    """
    개인정보 자동 검열 (Privacy MCP)
    """
    if risk_level in ["CRITICAL", "HIGH"]:
        # 메시지 내용 가림 처리
        censored_message = {
            "sender": message["sender"],
            "text": "[⚠️ 위험 메시지가 차단되었습니다. 클릭하여 확인]",
            "original_text": encrypt(message["text"]),  # 암호화 저장
            "timestamp": message["timestamp"],
            "is_censored": True
        }

        # URL/계좌번호 자동 마스킹
        censored_message["masked_entities"] = mask_sensitive_data(message)

        return censored_message

    return message
```

#### HIGH (높은 위험)
```python
{
    "intervention_level": "HIGH",
    "actions": [
        "⚠️ 경고 배너 표시",
        "🔍 메시지 하이라이트 (노란색)",
        "🚫 URL 클릭 시 확인 팝업",
        "📞 차단 권장",
        "🚨 신고 버튼 노출"
    ],
    "user_message": "⚠️ 주의가 필요한 메시지입니다",
    "explanation": "이 메시지는 '지인/상사 사칭 (급전)' 유형으로 분류되었습니다.",
    "recommended_actions": [
        "발신자에게 직접 전화하여 확인하세요",
        "요청에 즉시 응하지 마세요",
        "의심스러운 경우 차단하세요"
    ]
}
```

#### MEDIUM (중간 위험)
```python
{
    "intervention_level": "MEDIUM",
    "actions": [
        "ℹ️ 주의 알림 (작은 아이콘)",
        "🔍 메시지 하이라이트 (연한 노란색)",
        "❓ '이 메시지가 의심스럽나요?' 버튼"
    ],
    "user_message": "ℹ️ 일부 의심 패턴이 감지되었습니다",
    "explanation": "이 메시지는 '결제 승인 (낚시성)' 유형으로 분류되었습니다.",
    "recommended_actions": [
        "발신 번호를 확인하세요",
        "의심스러운 경우 공식 고객센터에 문의하세요"
    ]
}
```

#### LOW / SAFE (낮은 위험 / 안전)
```python
{
    "intervention_level": "SAFE",
    "actions": [],
    "user_message": None,
    "explanation": "안전한 메시지로 판단됩니다."
}
```

**Verification MCP 연동**:
```python
async def user_verification_flow(risk_level: str, category: str) -> bool:
    """
    사용자 확인 프로세스 (Verification MCP)
    """
    if risk_level == "CRITICAL":
        # 2단계 확인 요구
        confirmation_1 = await show_warning_popup(
            message="이 메시지는 사기/피싱 의심 메시지입니다. 정말 보시겠습니까?"
        )

        if confirmation_1:
            confirmation_2 = await show_final_warning(
                message="경고를 무시하고 계속하시면 개인정보 및 금전적 피해가 발생할 수 있습니다."
            )
            return confirmation_2

        return False

    return True  # LOW/MEDIUM은 자동 허용
```

---

## MECE 9-카테고리 체계

### Category A. 관계 사칭형 (Targeting Trust)

**핵심 기제**: 기존의 신뢰 관계(가족, 지인)를 도용하여 의심을 차단

| 카테고리 | 설명 | 기본 위험도 | 주요 시나리오 |
|---------|------|-----------|-------------|
| **A-1** | 가족 사칭 (액정 파손) | CRITICAL | "엄마, 나 폰 액정 깨져서 급해. 이 링크 깔아줘 bit.ly/xxx" |
| **A-2** | 지인/상사 사칭 (급전) | HIGH | "김 대리, 나 지금 미팅 중이라 폰뱅킹이 안 되는데 거래처에 급하게 300만 원만 먼저 보내줄 수 있나?" |
| **A-3** | 상품권 대리 구매 | HIGH | "이모, 내가 지금 결제가 안 돼서 그러는데 편의점 가서 구글 기프트카드 10만 원짜리 5개만 사서 뒤에 핀번호 사진 찍어 보내줄 수 있어?" |

**주요 채널**: 카카오톡, 텔레그램

**탐지 패턴**:
- 가족/지인 호칭 + 긴급 상황
- 폰 고장/분실 핑계로 전화 통화 회피
- 원격 제어 앱 설치 요구
- 계좌 이체 또는 상품권 구매 요청

---

### Category B. 공포/권위 악용형 (Targeting Fear & Authority)

**핵심 기제**: 공공기관이나 기업을 사칭하여 공포심(법적 조치)이나 긴급성(배송 오류)을 자극

| 카테고리 | 설명 | 기본 위험도 | 주요 시나리오 |
|---------|------|-----------|-------------|
| **B-1** | 생활 밀착형 (택배/경조사) | HIGH | "[CJ대한통운] 운송장번호 주소 불일치로 배송이 보류되었습니다. 주소 수정: bit.ly/xxx" |
| **B-2** | 기관 사칭 (건강/법무) | CRITICAL | "[국민건강보험] 건강검진 결과 통보서 발송완료. 내용확인: han.gl/xxx" |
| **B-3** | 결제 승인 (낚시성) | MEDIUM | "[국외발신] 아마존 해외결제 980,000원 완료. 본인 아닐 시 즉시 문의: 02-XXX-XXXX" |

**주요 채널**: SMS (문자) → 악성 URL 클릭 유도

**탐지 패턴**:
- 공공기관/택배사/금융사 사칭
- 법적 조치/과태료/배송 문제 언급
- 단축 URL 포함
- 긴급성 강조

---

### Category C. 욕망/감정 자극형 (Targeting Desire & Emotion)

**핵심 기제**: 새로운 관계를 형성하여 장기간 신뢰를 쌓은 후 금전을 요구

| 카테고리 | 설명 | 기본 위험도 | 주요 시나리오 |
|---------|------|-----------|-------------|
| **C-1** | 투자 권유 (리딩방) | HIGH | "00님, 이번에 세력 매집주 정보 입수했습니다. 300% 수익 보장합니다. 체험방 들어오세요." |
| **C-2** | 로맨스 스캠 | CRITICAL | "자기야, 내가 한국으로 짐(현금 상자)을 보냈는데 세관에 걸려서 통관비 500만 원이 필요해." |
| **C-3** | 몸캠 피싱 | CRITICAL | "오빠 목소리가 잘 안 들려. 이 앱 깔면 화질도 좋고 소리도 잘 들려. 이거 깔고 다시 하자." |

**주요 채널**: 인스타그램/데이팅앱 → 카카오톡/텔레그램

**탐지 패턴**:
- 고수익 투자 유혹
- 외국인/전문직 사칭
- 통관비/병원비 등 명목 금전 요구
- 영상 통화 + 앱 설치 요구

---

### NORMAL (정상 메시지)

**기본 위험도**: SAFE

**특징**: 위 9개 카테고리에 해당하지 않는 일반적인 대화

---

## MCP 서버 상세 설계

### 1. Context Analyzer MCP

**역할**: 대화 맥락 분석 및 카테고리 분류

**기술 스택**:
- Kanana 2.0 on-device LLM
- Prompt Engineering
- Few-shot Learning

**API 인터페이스**:
```python
class ContextAnalyzerMCP:
    async def analyze_context(
        self,
        conversation_history: List[Dict],
        current_message: Dict
    ) -> CategoryResult:
        """
        대화 맥락 분석 및 카테고리 분류

        Returns:
            CategoryResult: {
                category: str,
                category_name: str,
                confidence: float,
                reasoning: str,
                matched_patterns: List[str]
            }
        """
        pass
```

**프롬프트 템플릿**: [Kanana 2.0 LLM 통합](#kanana-20-llm-통합) 섹션 참조

---

### 2. Entity Extractor MCP

**역할**: 위협 식별자 추출 (URL, 계좌번호, 전화번호)

**기술 스택**:
- NER (Named Entity Recognition)
- 정규식 (Regex)
- URL Expander (단축 URL 확장)

**API 인터페이스**:
```python
class EntityExtractorMCP:
    async def extract_entities(self, message: str) -> EntityResult:
        """
        메시지에서 위협 식별자 추출

        Returns:
            EntityResult: {
                has_identifiers: bool,
                urls: List[str],
                urls_expanded: List[str],
                accounts: List[str],
                phones: List[str],
                amounts: List[str]
            }
        """
        pass
```

**추출 규칙**:
```python
EXTRACTION_PATTERNS = {
    "url": r'https?://[^\s]+|bit\.ly/[^\s]+|han\.gl/[^\s]+',
    "account": r'\d{3,4}-\d{2,6}-\d{2,6}',
    "phone": r'01[016789]-\d{3,4}-\d{4}',
    "amount": r'\d+만\s?원|\d+천\s?원|\d+억\s?원'
}
```

---

### 3. Threat Intelligence MCP

**역할**: 외부 신고 DB와 교차 검증

**기술 스택**:
- KISA 피싱사이트 탐지 API
- TheCheat 사기 신고 DB API
- Google Safe Browsing API (선택)

**API 인터페이스**:
```python
class ThreatIntelligenceMCP:
    async def check_threat_databases(
        self,
        entities: EntityResult
    ) -> ThreatIntelResult:
        """
        신고 DB 교차 검증

        Returns:
            ThreatIntelResult: {
                has_reported: bool,
                reported_items: List[ReportedItem],
                max_risk_score: int,
                recommendation: str
            }
        """
        pass
```

**외부 API 연동**:
```python
# KISA API 연동
async def check_kisa_api(url: str) -> Dict:
    endpoint = "https://api.kisa.or.kr/phishing/check"
    params = {"url": url, "api_key": KISA_API_KEY}
    response = await http_client.get(endpoint, params=params)
    return response.json()

# TheCheat API 연동
async def check_thecheat_api(
    account: Optional[str] = None,
    phone: Optional[str] = None
) -> Dict:
    endpoint = "https://api.thecheat.co.kr/report/check"
    params = {
        "account": account,
        "phone": phone,
        "api_key": THECHEAT_API_KEY
    }
    response = await http_client.get(endpoint, params=params)
    return response.json()
```

---

### 4. Social Graph MCP

**역할**: 발신자 신뢰도 분석

**기술 스택**:
- Kanana 2.0 on-device LLM
- 대화 이력 분석
- 패턴 매칭

**API 인터페이스**:
```python
class SocialGraphMCP:
    async def analyze_sender_trust(
        self,
        sender_id: str,
        conversation_history: List[Dict],
        current_message: Dict
    ) -> SenderTrustResult:
        """
        발신자 신뢰도 분석

        Returns:
            SenderTrustResult: {
                trust_level: str,  # high | medium | low
                trust_score: int,  # 0~100
                risk_adjustment: int,  # -1 | 0 | +1
                trust_factors: List[str],
                reasoning: str
            }
        """
        pass
```

**프롬프트 템플릿**: [Kanana 2.0 LLM 통합](#kanana-20-llm-통합) 섹션 참조

---

### 5. Decision Engine MCP

**역할**: 최종 위험도 종합 판단

**기술 스택**:
- 규칙 기반 의사결정
- 우선순위 로직
- 위험도 조정 알고리즘

**API 인터페이스**:
```python
class DecisionEngineMCP:
    async def determine_final_risk(
        self,
        category_result: CategoryResult,
        entity_result: EntityResult,
        threat_intel_result: ThreatIntelResult,
        sender_trust_result: SenderTrustResult
    ) -> FinalDecision:
        """
        최종 위험도 결정

        Returns:
            FinalDecision: {
                final_risk_level: str,
                base_risk_level: str,
                category: str,
                category_name: str,
                overridden_by: Optional[str],
                recommendation: str
            }
        """
        pass
```

**의사결정 규칙**:
```python
def decision_rules(
    threat_intel: ThreatIntelResult,
    category_result: CategoryResult,
    sender_trust: SenderTrustResult
) -> str:
    """
    우선순위 기반 의사결정

    1. 신고 DB 이력 → CRITICAL (절대 우선)
    2. 카테고리 기본 위험도
    3. 발신자 신뢰도 조정 (±1 단계)
    """
    if threat_intel.has_reported:
        return "CRITICAL"

    base_risk = CATEGORY_BASE_RISK[category_result.category]
    adjusted_risk = adjust_risk_level(base_risk, sender_trust.risk_adjustment)

    return adjusted_risk
```

---

### 6. Privacy MCP

**역할**: 개인정보 보호 및 자동 검열

**기술 스택**:
- 텍스트 마스킹
- 암호화 (AES-256)
- 접근 제어

**API 인터페이스**:
```python
class PrivacyMCP:
    async def apply_privacy_protection(
        self,
        message: Dict,
        risk_level: str
    ) -> CensoredMessage:
        """
        개인정보 자동 검열

        Returns:
            CensoredMessage: {
                sender: str,
                text: str,  # 가려진 텍스트
                original_text: str,  # 암호화된 원본
                is_censored: bool,
                masked_entities: Dict
            }
        """
        pass
```

**검열 규칙**:
```python
CENSORSHIP_RULES = {
    "CRITICAL": {
        "mask_message": True,
        "mask_urls": True,
        "mask_accounts": True,
        "mask_phones": True,
        "block_clicks": True
    },
    "HIGH": {
        "mask_message": False,
        "mask_urls": True,
        "mask_accounts": True,
        "mask_phones": False,
        "block_clicks": False
    },
    "MEDIUM": {
        "mask_message": False,
        "mask_urls": False,
        "mask_accounts": False,
        "mask_phones": False,
        "block_clicks": False
    }
}
```

---

### 7. Verification MCP

**역할**: 사용자 확인 프로세스

**기술 스택**:
- UI 팝업 관리
- 사용자 피드백 수집
- 학습 데이터 생성

**API 인터페이스**:
```python
class VerificationMCP:
    async def request_user_verification(
        self,
        risk_level: str,
        category: str,
        message: Dict
    ) -> VerificationResult:
        """
        사용자 확인 요청

        Returns:
            VerificationResult: {
                user_confirmed: bool,
                user_feedback: Optional[str],
                timestamp: str
            }
        """
        pass
```

**확인 프로세스**:
```python
async def verification_flow(risk_level: str) -> bool:
    """
    위험도별 확인 단계

    CRITICAL: 2단계 확인 요구
    HIGH: 1단계 확인 요구
    MEDIUM: 경고 표시만
    LOW/SAFE: 확인 불필요
    """
    if risk_level == "CRITICAL":
        step1 = await show_warning_popup()
        if step1:
            step2 = await show_final_warning()
            return step2
        return False

    elif risk_level == "HIGH":
        return await show_warning_popup()

    return True
```

---

## Kanana 2.0 LLM 통합

### 카테고리 분류 프롬프트 (Stage ①)

```
# 역할
당신은 메신저 피싱/사기 메시지 분류 전문가입니다.

# 작업
수신된 메시지를 분석하여 9개 사기 유형 카테고리 중 하나로 분류하세요.

# 카테고리 정의

## Category A. 관계 사칭형 (Targeting Trust)
- A-1: 가족 사칭 (액정 파손)
  - 핵심 패턴: 가족 호칭 + 폰 고장 핑계 + 앱/링크 설치 요구
  - 예시: "엄마, 나 폰 액정 깨져서 급해. 이 링크 깔아줘 bit.ly/xxx"

- A-2: 지인/상사 사칭 (급전)
  - 핵심 패턴: 지인/상사 호칭 + 급한 사정 + 계좌 이체 요청
  - 예시: "김 대리, 나 지금 미팅 중이라 폰뱅킹이 안 되는데 거래처에 급하게 300만 원만 먼저 보내줄 수 있나?"

- A-3: 상품권 대리 구매
  - 핵심 패턴: 결제 불가 핑계 + 상품권 구매 요청 + 핀번호 요구
  - 예시: "이모, 내가 지금 결제가 안 돼서 그러는데 편의점 가서 구글 기프트카드 10만 원짜리 5개만 사서 뒤에 핀번호 사진 찍어 보내줄 수 있어?"

## Category B. 공포/권위 악용형 (Targeting Fear & Authority)
- B-1: 생활 밀착형 (택배/경조사)
  - 핵심 패턴: 택배사 사칭 + 배송 문제 + 단축 URL
  - 예시: "[CJ대한통운] 운송장번호 주소 불일치로 배송이 보류되었습니다. 주소 수정: bit.ly/xxx"

- B-2: 기관 사칭 (건강/법무)
  - 핵심 패턴: 공공기관 사칭 + 법적 조치/건강검진 + URL
  - 예시: "[국민건강보험] 건강검진 결과 통보서 발송완료. 내용확인: han.gl/xxx"

- B-3: 결제 승인 (낚시성)
  - 핵심 패턴: 고액 해외결제 알림 + 문의 번호
  - 예시: "[국외발신] 아마존 해외결제 980,000원 완료. 본인 아닐 시 즉시 문의: 02-XXX-XXXX"

## Category C. 욕망/감정 자극형 (Targeting Desire & Emotion)
- C-1: 투자 권유 (리딩방)
  - 핵심 패턴: 고수익 투자 유혹 + 리딩방 초대 + 수익 보장
  - 예시: "00님, 이번에 세력 매집주 정보 입수했습니다. 300% 수익 보장합니다. 체험방 들어오세요."

- C-2: 로맨스 스캠
  - 핵심 패턴: 외국인/전문직 사칭 + 금전 요구 (통관비/병원비)
  - 예시: "자기야, 내가 한국으로 짐(현금 상자)을 보냈는데 세관에 걸려서 통관비 500만 원이 필요해."

- C-3: 몸캠 피싱
  - 핵심 패턴: 영상 통화 + 소리/화질 문제 핑계 + 앱 설치 요구
  - 예시: "오빠 목소리가 잘 안 들려. 이 앱 깔면 화질도 좋고 소리도 잘 들려. 이거 깔고 다시 하자."

## NORMAL
- 위 9개 카테고리에 해당하지 않는 일반 메시지

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

# 출력 형식 (JSON)
{
  "category": "A-1",
  "category_name": "가족 사칭 (액정 파손)",
  "confidence": 0.92,
  "reasoning": "가족 호칭(엄마) + 긴급 상황(액정 파손) + URL 요청 패턴이 A-1 시나리오와 일치",
  "matched_patterns": [
    "가족 호칭 사용",
    "긴급성 언어 (급해)",
    "단축 URL 포함 (bit.ly)",
    "앱/링크 설치 요구"
  ],
  "context_anomalies": [
    "평소 일상 대화 → 갑작스러운 긴급 요청",
    "이전 대화에서 URL 요청 이력 없음"
  ]
}
```

---

### 발신자 신뢰도 분석 프롬프트 (Stage ④)

```
# 역할
당신은 대화 맥락 분석 전문가입니다.

# 작업
발신자와의 대화 이력을 분석하여 신뢰도를 평가하고, 현재 메시지의 위험도를 조정하세요.

# 분석 기준 (예시 기반 학습)

## 1. 대화 톤/스타일 일관성

정상 패턴 예시:
- "엄마~", "엄마!", "엄마," (일관된 호칭)
- 맞춤법/띄어쓰기 일관성
- 이모티콘 사용 패턴 유지
- 문장 구조 일관성

의심 패턴 예시:
- [평소] "엄마~" → [현재] "어머니" (호칭 변화)
- [평소] 정확한 맞춤법 → [현재] 오타 많음
- [평소] ㅋㅋ 사용 → [현재] ㅎㅎ 사용
- 번역기 투 한국어

## 2. 갑작스러운 금전/행동 요청

정상 패턴 예시:
- 장기 대화 후 자연스러운 요청
- "다음주 등록금 납부 기간인데 입금해줄 수 있어?"
- 사전에 요청 내용 언급

의심 패턴 예시:
- 대화 없다가 갑자기 금전 요청
- 첫 메시지부터 "급하게 300만원 보내줘"
- 링크 설치, 앱 다운로드 요구
- 상품권 구매 요청

## 3. 평소와 다른 말투

정상 패턴 예시:
- 일관된 문장 구조
- 평소 사용하는 표현 반복
- 자연스러운 대화 흐름

의심 패턴 예시:
- 지나치게 격식적/비격식적
- 평소 사용하지 않는 이모티콘/줄임말
- 어색한 표현, 부자연스러운 한국어

## 4. 장기 대화 이력

고신뢰 (high):
- 30일 이상 지속적 대화
- 100+ 메시지 교환
- 일상적 주제 다수 (밥, 날씨, 안부 등)
→ risk_adjustment: -1 (위험도 낮춤)

중신뢰 (medium):
- 7~30일 대화
- 20~100 메시지
- 일부 일상적 주제
→ risk_adjustment: 0 (유지)

저신뢰 (low):
- 7일 미만 대화
- 20개 미만 메시지
- 갑작스러운 금전 요청
→ risk_adjustment: +1 (위험도 높임)

# 대화 이력
{conversation_history}

# 현재 메시지
{current_message}

# 발신자 메타데이터
{sender_metadata}

# 신뢰도 레벨 기준
- high: 장기 대화, 일관된 톤, 자연스러운 요청 → risk_adjustment: -1
- medium: 중기 대화, 대체로 일관됨 → risk_adjustment: 0
- low: 짧은 대화, 갑작스러운 요청, 톤 변화 → risk_adjustment: +1

# 출력 형식 (JSON)
{
  "trust_level": "low",
  "trust_score": 25,
  "risk_adjustment": +1,
  "trust_factors": [
    "⚠️ 갑작스러운 금전 요청",
    "⚠️ 평소와 다른 말투 (링크 요청)",
    "⚠️ 대화 이력 부족 (최근 3일간만 대화)",
    "⚠️ 톤 변화 감지 (일상 대화 → 긴급 요청)"
  ],
  "reasoning": "평소 일상적인 대화만 하던 발신자가 갑자기 긴급 상황을 언급하며 링크 설치를 요구하는 패턴은 계정 도용 또는 사칭 가능성이 높음",
  "conversation_metadata": {
    "total_days": 3,
    "total_messages": 8,
    "tone_consistency_score": 0.45,
    "request_pattern_abnormal": true
  }
}
```

---

## 구현 계획

### Phase 1: 문서화 및 설계 ✅ (현재 단계)
- [x] 시스템 설계 문서 작성
- [x] MECE 카테고리 체계 정리
- [x] MCP 아키텍처 설계
- [x] 프롬프트 설계
- [ ] 사용자 검토 및 피드백

---

### Phase 2: MCP 서버 구현 (2주)

#### Week 1: 핵심 MCP 서버
1. **Context Analyzer MCP**
   - Kanana 2.0 API 연동
   - 카테고리 분류 프롬프트 최적화
   - Few-shot 예시 데이터셋 준비
   - 단위 테스트 (9개 카테고리별 정확도 >90%)

2. **Entity Extractor MCP**
   - NER 모델 통합
   - 정규식 패턴 정의
   - URL Expander 구현
   - 단위 테스트 (추출 정확도 >95%)

3. **Threat Intelligence MCP**
   - KISA API 연동
   - TheCheat API 연동
   - 캐싱 레이어 구현
   - 단위 테스트 (API 응답 처리)

#### Week 2: 지원 MCP 서버
4. **Social Graph MCP**
   - Kanana 2.0 신뢰도 분석 프롬프트
   - 대화 이력 분석 로직
   - 단위 테스트 (신뢰도 평가 정확도)

5. **Decision Engine MCP**
   - 우선순위 로직 구현
   - 위험도 조정 알고리즘
   - 단위 테스트 (의사결정 규칙)

6. **Privacy MCP + Verification MCP**
   - 텍스트 마스킹 구현
   - 암호화 모듈
   - UI 팝업 인터페이스
   - 단위 테스트 (검열 규칙)

**디렉토리 구조**:
```
testdata/KAT/
├── agent/
│   ├── mcp_servers/
│   │   ├── __init__.py
│   │   ├── context_analyzer.py      # Stage ①
│   │   ├── entity_extractor.py      # Stage ②
│   │   ├── threat_intelligence.py   # Stage ③
│   │   ├── social_graph.py          # Stage ④
│   │   ├── decision_engine.py       # Stage ⑤
│   │   ├── privacy.py               # Privacy MCP
│   │   └── verification.py          # Verification MCP
│   ├── core/
│   │   ├── threat_matcher.py        # 기존 (수정)
│   │   └── action_policy.py         # 기존 (수정)
│   └── data/
│       ├── scam_categories.json     # 카테고리 정의
│       └── prompts/
│           ├── category_classification.txt
│           └── sender_trust_analysis.txt
```

---

### Phase 3: 통합 및 테스트 (1주)

1. **6단계 파이프라인 통합**
   - MCP 서버 간 데이터 흐름 구현
   - 에러 처리 및 재시도 로직
   - 성능 최적화 (병렬 처리)

2. **통합 테스트**
   - 전체 파이프라인 E2E 테스트
   - 실제 사기 메시지 데이터 100건 테스트
   - False Positive/Negative 측정

3. **성능 테스트**
   - Kanana 2.0 추론 속도 측정
   - 메모리 사용량 프로파일링
   - 응답 시간 최적화 (목표: <500ms)

**테스트 데이터셋**:
```
testdata/KAT/tests/
├── test_data/
│   ├── category_a/
│   │   ├── a1_samples.json  # 100건
│   │   ├── a2_samples.json  # 100건
│   │   └── a3_samples.json  # 100건
│   ├── category_b/
│   │   ├── b1_samples.json  # 100건
│   │   ├── b2_samples.json  # 100건
│   │   └── b3_samples.json  # 100건
│   ├── category_c/
│   │   ├── c1_samples.json  # 100건
│   │   ├── c2_samples.json  # 100건
│   │   └── c3_samples.json  # 100건
│   └── normal_samples.json  # 300건
```

---

### Phase 4: Kanana 2.0 프롬프트 최적화 (1주)

1. **Few-shot 예시 최적화**
   - 카테고리별 대표 예시 선정 (5개씩)
   - 경계 케이스 예시 추가
   - 프롬프트 A/B 테스트

2. **신뢰도 분석 프롬프트 개선**
   - 대화 이력 분석 예시 추가
   - 톤 변화 감지 패턴 정교화
   - 거짓 긍정 감소 목표

3. **성능 평가**
   - 카테고리 분류 정확도 측정 (목표: >88%)
   - 신뢰도 분석 정확도 측정 (목표: >85%)
   - Confidence 보정

---

### Phase 5: 배포 및 모니터링 (1주)

1. **스테이징 배포**
   - 백엔드 서버 배포
   - 프론트엔드 통합

2. **A/B 테스트**
   - 기존 시스템 vs 새 시스템 비교
   - 사용자 피드백 수집

3. **모니터링**
   - 실시간 정확도 모니터링
   - False Positive/Negative 추적
   - 사용자 신고 분석

4. **지속적 개선**
   - 새로운 사기 유형 발견 시 카테고리 추가
   - Kanana 2.0 프롬프트 업데이트
   - MCP 서버 성능 튜닝

---

## 부록

### A. 카테고리별 특징 요약

| 카테고리 | 핵심 키워드 | 주요 채널 | 기본 위험도 |
|---------|-----------|----------|-----------|
| A-1 | 가족, 액정, 앱 설치 | 카카오톡 | CRITICAL |
| A-2 | 지인, 급전, 송금 | 카카오톡 | HIGH |
| A-3 | 상품권, 핀번호 | 카카오톡 | HIGH |
| B-1 | 택배, 주소, URL | SMS | HIGH |
| B-2 | 기관, 건강검진, 과태료 | SMS | CRITICAL |
| B-3 | 해외결제, 고액 | SMS | MEDIUM |
| C-1 | 투자, 수익, 리딩방 | 카카오톡/텔레그램 | HIGH |
| C-2 | 외국인, 통관비 | 카카오톡 | CRITICAL |
| C-3 | 영상, 앱 설치, 화질 | 카카오톡 | CRITICAL |

---

### B. 위험도별 통계 (예상)

| 위험도 | 카테고리 수 | 예상 비율 |
|--------|-----------|----------|
| CRITICAL | A-1, B-2, C-2, C-3 | 40% |
| HIGH | A-2, A-3, B-1, C-1 | 35% |
| MEDIUM | B-3 | 10% |
| SAFE | NORMAL | 15% |

---

### C. 외부 API 목록

| API | 용도 | Stage | 문서 |
|-----|------|-------|------|
| KISA 피싱사이트 탐지 | URL 검증 | ③ | https://api.kisa.or.kr/docs |
| TheCheat | 계좌/번호 신고 조회 | ③ | https://api.thecheat.co.kr/docs |
| Kanana 2.0 | 온디바이스 LLM | ①④ | 내부 문서 |

---

### D. 성능 목표

| 지표 | 목표 | 측정 방법 |
|-----|------|----------|
| 카테고리 분류 정확도 | >88% | 테스트 데이터셋 900건 |
| 신뢰도 분석 정확도 | >85% | 수동 레이블링 데이터 |
| False Positive | <5% | 정상 메시지 300건 |
| False Negative | <8% | 사기 메시지 900건 |
| 응답 시간 | <500ms | 평균 처리 시간 |
| Kanana 2.0 추론 시간 | <200ms | 온디바이스 측정 |

---

### E. 참고 자료

- AIagent_20251117_V0.7.pdf (기획서)
- guide/Agent B 카테고리 분류 _ 원칙.md (MECE 카테고리)
- KISA 피싱사이트 탐지 가이드
- TheCheat 사기 신고 DB 스키마
- Kanana 2.0 온디바이스 모델 문서

---

**문서 종료**
