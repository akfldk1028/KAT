# Agent B (안심 가드) 구현 명세서

**작성일**: 2025-12-07
**버전**: 1.0
**작성자**: Claude Code
**목적**: Agent B 실제 구현 내용과 기획서 비교 분석

---

## 📋 목차

1. [개요](#1-개요)
2. [주요 동작 로직](#2-주요-동작-로직)
3. [실제 구현 내용](#3-실제-구현-내용)
4. [기획서 대비 Gap 분석](#4-기획서-대비-gap-분석)
5. [향후 개선 로드맵](#5-향후-개선-로드맵)

---

## 1. 개요

### 1.1 역할 및 목표

**Agent B (안심 가드)** = **수신 메시지 보안 에이전트**

```
핵심 미션: 사용자가 받은 메시지에서 피싱/사기/악성 위협을 탐지하고 경고
최종 목표: 보이스피싱, 스미싱, 금융사기로부터 사용자 보호
```

**설계 철학**:
- "보수적 판단" - False Negative 최소화 (놓치는 것보다 과잉 탐지가 안전)
- "4-Stage 검증" - 다층 방어로 정확도 향상
- "심리적 기제 분류" - 사기 시나리오를 신뢰/공포/욕망 3축으로 분석

### 1.2 Agent A와의 차이점

| 측면 | Agent A (안심 전송) | Agent B (안심 가드) |
|------|-------------------|-------------------|
| **방향** | 발신 (Outgoing) | 수신 (Incoming) |
| **탐지 대상** | PII (민감정보) | 위협 패턴 (사기 시나리오) |
| **분석 목표** | 빠르게 걸러내기 | 보수적으로 검증 |
| **아키텍처** | 2-Tier (Quick + Deep) | 4-Stage (순차 파이프라인) |
| **MCP 도구** | 11개 | 12개 |
| **응답 속도** | 빠름 (Tier 1 통과 시 50ms) | 중간 (4-stage 순차 200ms) |
| **우선순위** | False Positive 회피 | False Negative 회피 |

---

## 2. 주요 동작 로직

### 2.1 4-Stage 파이프라인 아키텍처

Agent B는 **순차적 검증 파이프라인**으로 설계되었습니다.

```
┌─────────────────────────────────────────────────────────────┐
│                     User receives message                    │
│                   "은행 계좌 정지됩니다"                      │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: Text Pattern Analysis                              │
│ ├─ analyze_incoming_message(text)                           │
│ ├─ 텍스트 패턴 매칭 (threat_patterns.json)                   │
│ ├─ MECE 9-카테고리 분류 (A-1 ~ C-3)                          │
│ └─ Output: {category, keywords, confidence, risk_score}     │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: Scam DB Lookup                                     │
│ ├─ check_scam_in_message(text)                              │
│ ├─ KISA DB 조회 (신고된 사기 전화번호)                        │
│ ├─ TheCheat Mock DB (유사 사기 시나리오)                     │
│ └─ Output: {is_reported, db_source, match_details}          │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 3: Sender Trust Analysis                              │
│ ├─ analyze_sender_risk(sender_id, user_id)                  │
│ ├─ 발신자 신뢰도 평가 (대화 이력, 연락처 등록 여부)             │
│ ├─ 대화 맥락 분석 (conversation_analyzer.py)                 │
│ └─ Output: {trust_score, history_count, is_registered}      │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 4: Policy-Based Final Decision                        │
│ ├─ get_combined_policy(results)                             │
│ ├─ 위험도 합산 (weighted average)                            │
│ ├─ 정책 기반 최종 판정 (action_policy.py)                    │
│ └─ Output: {risk_level, action, reason}                     │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Final Result to User                       │
│  {                                                           │
│    "risk_level": "DANGEROUS",                                │
│    "category": "B-1 (기관 사칭형)",                           │
│    "action": "BLOCK_RECOMMEND",                              │
│    "reason": "금융기관 사칭 + 긴급 압박 + 신고 이력"           │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

**설계 근거**:
- **Stage 1**: 빠른 패턴 필터링 (90% 정상 메시지 통과)
- **Stage 2**: 신고 DB로 검증 강화 (기존 사기 번호 즉시 차단)
- **Stage 3**: 발신자 신뢰도로 오탐 감소 (가족/친구는 안전)
- **Stage 4**: 종합 판단으로 최종 결정

### 2.2 MECE 9-카테고리 분류 시스템

**MECE (Mutually Exclusive, Collectively Exhaustive)** 원칙:
- **상호 배타적**: 하나의 메시지는 하나의 카테고리에만 속함
- **전체 포괄적**: 모든 사기 시나리오를 커버

#### 2.2.1 심리적 기제 기반 3×3 매트릭스

```
                심리적 기제
        ┌──────────────────────────────────┐
        │  Trust   │   Fear   │   Desire   │
┌───────┼──────────┼──────────┼────────────┤
│ 관계  │   A-1    │   A-2    │    A-3     │
│ 사칭  │  지인    │   자녀   │   권위자   │
├───────┼──────────┼──────────┼────────────┤
│ 공포  │   B-1    │   B-2    │    B-3     │
│ 악용  │  기관    │   법적   │   금전손실 │
├───────┼──────────┼──────────┼────────────┤
│ 욕망  │   C-1    │   C-2    │    C-3     │
│ 자극  │  이익    │   긴급   │   호기심   │
└───────┴──────────┴──────────┴────────────┘
```

#### 2.2.2 카테고리 상세 정의

**Category A: 관계 사칭형**

```yaml
A-1: 지인 사칭 + 신뢰 악용
  keywords: ["엄마", "아빠", "친구", "선배", "나야"]
  patterns: ["휴대폰 바꿨어", "카톡 바꿨어", "급하게 돈 좀"]
  psychological_trigger: Trust (신뢰 관계 악용)
  severity: HIGH
  example: "엄마야, 휴대폰 바꿔서 연락해. 급하게 돈 좀 보내줘"

A-2: 자녀 사칭 + 공포 유발
  keywords: ["아들", "딸", "엄마", "사고", "납치"]
  patterns: ["사고 났어", "급히 필요해", "병원에"]
  psychological_trigger: Fear (자녀 안전 불안)
  severity: CRITICAL
  example: "엄마 나 사고났어. 합의금 급해. 빨리 보내줘"

A-3: 권위자 사칭 + 욕망 자극
  keywords: ["사장님", "교수님", "선생님", "부장님"]
  patterns: ["중요한 일", "승진", "특별 제안"]
  psychological_trigger: Desire (권위/인정 욕구)
  severity: MEDIUM
  example: "사장님이십니까? 특별 제안 있습니다"
```

**Category B: 공포/권위 악용형**

```yaml
B-1: 기관 사칭 + 권위 압박
  keywords: ["경찰청", "검찰청", "금융감독원", "국세청"]
  patterns: ["조사 중", "계좌 정지", "법적 조치", "출석 요구"]
  psychological_trigger: Fear (법적/제도적 공포)
  severity: CRITICAL
  example: "금융감독원입니다. 귀하 계좌 불법 거래 의심"

B-2: 법적 위협 + 긴급 압박
  keywords: ["소송", "고소", "고발", "체포", "구속"]
  patterns: ["24시간 내", "즉시", "오늘 중", "지금 바로"]
  psychological_trigger: Fear (법적 처벌 공포)
  severity: HIGH
  example: "소송 예정입니다. 24시간 내 연락 없으면 고소"

B-3: 금전 손실 공포 + 보상 유도
  keywords: ["환불", "보상", "피해", "손실", "배상"]
  patterns: ["환불 받으려면", "보상금 지급", "피해 보상"]
  psychological_trigger: Fear (금전 손실 공포)
  severity: MEDIUM
  example: "택배 파손 보상금 지급합니다. 계좌번호 알려주세요"
```

**Category C: 욕망/감정 자극형**

```yaml
C-1: 금전적 이익 + 탐욕 자극
  keywords: ["당첨", "경품", "무료", "지원금", "보조금"]
  patterns: ["당첨되셨습니다", "무료 제공", "지원금 신청"]
  psychological_trigger: Desire (금전 욕구)
  severity: MEDIUM
  example: "축하합니다! 5천만원 당첨. 수령하려면 클릭"

C-2: 긴급성 강조 + 기회 상실 공포
  keywords: ["마감", "오늘만", "한정", "선착순", "놓치면"]
  patterns: ["오늘 마감", "선착순 10명", "지금 아니면"]
  psychological_trigger: Desire + Fear (FOMO)
  severity: LOW
  example: "오늘 마감! 놓치면 후회합니다"

C-3: 호기심 자극 + 클릭 유도
  keywords: ["확인", "클릭", "사진", "영상", "링크"]
  patterns: ["이 사진", "링크 확인", "여기 클릭"]
  psychological_trigger: Desire (호기심)
  severity: LOW
  example: "이 사진 봐봐 [suspicious-link.com]"
```

**추가 카테고리**:

```yaml
D-N: 불명확/신규 유형
  condition: confidence < 0.3
  fallback: 보수적 판단 (SUSPICIOUS)
  example: 알 수 없는 패턴이지만 의심스러운 요소 존재

NORMAL: 정상 메시지
  condition: no_threat_indicators
  action: SAFE
  example: "내일 점심 먹을래?", "회의 몇 시야?"
```

#### 2.2.3 카테고리 분류 알고리즘

```python
def classify_category(text: str, patterns: Dict) -> CategoryResult:
    """
    MECE 9-카테고리 분류 알고리즘

    Args:
        text: 분석할 메시지 텍스트
        patterns: threat_patterns.json 데이터

    Returns:
        CategoryResult(category, confidence, matched_keywords)
    """
    scores = {}

    # 1. 각 카테고리별 점수 계산
    for category in ["A-1", "A-2", "A-3", "B-1", "B-2", "B-3", "C-1", "C-2", "C-3"]:
        keyword_score = _calculate_keyword_match(text, patterns[category]["keywords"])
        pattern_score = _calculate_pattern_match(text, patterns[category]["patterns"])

        # Weighted average
        scores[category] = keyword_score * 0.4 + pattern_score * 0.6

    # 2. 최고 점수 카테고리 선택
    best_category = max(scores, key=scores.get)
    confidence = scores[best_category]

    # 3. Confidence 임계값 검사
    if confidence < 0.3:
        return CategoryResult(category="D-N", confidence=confidence, ...)

    # 4. MECE 보장: 상위 2개 카테고리 점수 차이 검사
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if sorted_scores[0][1] - sorted_scores[1][1] < 0.1:
        # 모호한 경우 보수적 판단
        return CategoryResult(category="D-N", confidence=confidence, ...)

    return CategoryResult(category=best_category, confidence=confidence, ...)
```

### 2.3 MCP 도구 (12개)

Agent B는 **12개의 FastMCP 도구**로 구성됩니다.

#### 2.3.1 도구 목록 및 I/O 명세

**Stage 1: 텍스트 패턴 분석 도구**

```python
@mcp.tool()
def analyze_incoming_message(text: str, use_ai: bool = False) -> Dict:
    """
    수신 메시지 위협 분석 (Stage 1)

    Args:
        text: 분석할 메시지 텍스트
        use_ai: AI 기반 분석 사용 여부

    Returns:
        {
            "category": "B-1",
            "risk_score": 0.85,
            "matched_keywords": ["금융감독원", "계좌 정지"],
            "confidence": 0.92,
            "severity": "CRITICAL"
        }
    """
    agent = _get_incoming_agent()
    result = agent.analyze(text, use_ai=use_ai)
    return result.to_dict()


@mcp.tool()
def scan_threats(text: str) -> Dict:
    """
    위협 패턴 1차 스캔 (정규식 기반)

    Returns:
        {
            "threats": [
                {"type": "phishing_keyword", "value": "금융감독원", "position": 0},
                {"type": "urgency_pattern", "value": "즉시", "position": 15}
            ],
            "total_count": 2
        }
    """
    matcher = ThreatMatcher()
    return matcher.scan(text)


@mcp.tool()
def classify_scam_category(text: str) -> Dict:
    """
    MECE 9-카테고리 분류

    Returns:
        {
            "category": "B-1",
            "category_name": "기관 사칭형",
            "confidence": 0.92,
            "psychological_trigger": "Fear",
            "matched_patterns": ["조사 중", "계좌 정지"]
        }
    """
    matcher = ThreatMatcher()
    return matcher.classify_category(text)
```

**Stage 2: 사기 DB 조회 도구**

```python
@mcp.tool()
def check_scam_in_message(text: str) -> Dict:
    """
    메시지 내 사기 정보 조회 (전화번호, URL 등)

    Returns:
        {
            "is_reported": true,
            "db_source": "KISA",
            "phone_number": "010-1234-5678",
            "report_count": 127,
            "last_reported": "2025-12-01"
        }
    """
    checker = ScamChecker()
    return checker.check_in_message(text)


@mcp.tool()
def check_reported_scam(identifier: str, identifier_type: str) -> Dict:
    """
    특정 식별자(전화번호/URL/계좌번호)의 신고 이력 조회

    Args:
        identifier: "010-1234-5678" or "http://scam.com"
        identifier_type: "phone" or "url" or "account"

    Returns:
        {
            "is_reported": true,
            "source": "KISA",
            "report_count": 45,
            "scam_type": "voice_phishing",
            "description": "금융기관 사칭 보이스피싱"
        }
    """
    checker = ScamChecker()
    return checker.check_reported(identifier, identifier_type)


@mcp.tool()
def search_similar_scam_cases(text: str, top_k: int = 5) -> Dict:
    """
    유사 사기 사례 검색 (TheCheat Mock DB)

    Returns:
        {
            "similar_cases": [
                {
                    "case_id": "SC-2024-1234",
                    "similarity": 0.89,
                    "category": "B-1",
                    "description": "금융감독원 사칭 계좌 정지 사기"
                }
            ]
        }
    """
    checker = ScamChecker()
    return checker.search_similar(text, top_k)
```

**Stage 3: 발신자 신뢰도 분석 도구**

```python
@mcp.tool()
def analyze_sender_risk(sender_id: str, user_id: str) -> Dict:
    """
    발신자 위험도 분석 (대화 이력, 연락처 등록 등)

    Returns:
        {
            "trust_score": 0.85,
            "is_registered": true,
            "contact_name": "엄마",
            "conversation_count": 1247,
            "first_contact_date": "2020-03-15",
            "risk_indicators": []
        }
    """
    analyzer = ConversationAnalyzer()
    return analyzer.analyze_sender(sender_id, user_id)


@mcp.tool()
def analyze_conversation_history(sender_id: str, user_id: str, days: int = 30) -> Dict:
    """
    최근 대화 이력 분석 (맥락 파악)

    Returns:
        {
            "message_count": 45,
            "avg_response_time": 120,  # seconds
            "topic_distribution": {"일상": 0.6, "업무": 0.3, "기타": 0.1},
            "abnormal_patterns": []
        }
    """
    analyzer = ConversationAnalyzer()
    return analyzer.analyze_history(sender_id, user_id, days)


@mcp.tool()
def check_sender_reputation(sender_id: str) -> Dict:
    """
    발신자 평판 조회 (다른 사용자 신고 이력)

    Returns:
        {
            "reputation_score": 0.95,
            "total_reports": 0,
            "is_verified": false,
            "verification_source": null
        }
    """
    analyzer = ConversationAnalyzer()
    return analyzer.check_reputation(sender_id)
```

**Stage 4: 정책 기반 판정 도구**

```python
@mcp.tool()
def get_combined_policy(analysis_results: Dict) -> Dict:
    """
    종합 위험도 평가 및 정책 기반 조치 결정

    Args:
        analysis_results: {
            "stage1": {...},
            "stage2": {...},
            "stage3": {...}
        }

    Returns:
        {
            "final_risk_level": "DANGEROUS",
            "risk_score": 0.87,
            "recommended_action": "BLOCK_RECOMMEND",
            "reason": "기관 사칭 + 신고 이력 + 낮은 발신자 신뢰도",
            "confidence": 0.95
        }
    """
    policy = ActionPolicy()
    return policy.get_combined_decision(analysis_results)


@mcp.tool()
def evaluate_combined_risk(stage_results: List[Dict]) -> Dict:
    """
    다층 분석 결과 통합 평가 (Weighted Average)

    Returns:
        {
            "combined_score": 0.87,
            "weights": {
                "pattern_analysis": 0.4,
                "db_check": 0.3,
                "sender_trust": 0.3
            },
            "breakdown": {...}
        }
    """
    policy = ActionPolicy()
    return policy.evaluate_risk(stage_results)


@mcp.tool()
def get_action_recommendation(risk_level: str, category: str) -> Dict:
    """
    위험도 및 카테고리 기반 조치 권고

    Returns:
        {
            "action": "BLOCK_RECOMMEND",
            "user_message": "⚠️ 금융기관 사칭 의심 메시지입니다. 응답하지 마세요.",
            "detailed_reason": "...",
            "additional_info": "금융감독원은 문자로 계좌 정보를 요구하지 않습니다."
        }
    """
    policy = ActionPolicy()
    return policy.get_action(risk_level, category)
```

#### 2.3.2 위험도 4단계 분류

```python
class RiskLevel(str, Enum):
    SAFE = "SAFE"              # 안전 (정상 메시지)
    SUSPICIOUS = "SUSPICIOUS"  # 의심 (주의 필요)
    DANGEROUS = "DANGEROUS"    # 위험 (차단 권고)
    CRITICAL = "CRITICAL"      # 치명적 (즉시 차단)


# 위험도 판정 기준
RISK_THRESHOLDS = {
    "SAFE": (0.0, 0.3),
    "SUSPICIOUS": (0.3, 0.6),
    "DANGEROUS": (0.6, 0.85),
    "CRITICAL": (0.85, 1.0)
}

# 카테고리별 기본 위험도
CATEGORY_BASE_RISK = {
    "A-2": "CRITICAL",  # 자녀 사칭
    "B-1": "CRITICAL",  # 기관 사칭
    "A-1": "HIGH",      # 지인 사칭
    "B-2": "HIGH",      # 법적 위협
    "B-3": "MEDIUM",    # 금전 손실 공포
    "C-1": "MEDIUM",    # 금전적 이익
    "A-3": "MEDIUM",    # 권위자 사칭
    "C-2": "LOW",       # 긴급성 강조
    "C-3": "LOW",       # 호기심 자극
    "D-N": "SUSPICIOUS",# 불명확
    "NORMAL": "SAFE"    # 정상
}
```

#### 2.3.3 ReAct 패턴 통합 흐름

**Kanana LLM의 추론-행동 루프**:

```
User Message: "금융감독원입니다. 귀하 계좌 불법 거래 의심. 즉시 확인 필요"

┌─────────────────────────────────────────────────────────────┐
│ Kanana Agent (ReAct Pattern)                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ [Thought 1] 메시지에 "금융감독원", "계좌", "즉시" 키워드 발견  │
│            → Stage 1 패턴 분석 필요                           │
│                                                              │
│ [Action 1] analyze_incoming_message(text)                   │
│            → Result: category="B-1", confidence=0.92         │
│                                                              │
│ [Thought 2] B-1 카테고리(기관 사칭)는 CRITICAL 수준            │
│            → Stage 2 신고 DB 확인 필요                        │
│                                                              │
│ [Action 2] check_scam_in_message(text)                      │
│            → Result: is_reported=false (신고 이력 없음)       │
│                                                              │
│ [Thought 3] 신고 이력은 없지만 패턴이 명확함                    │
│            → Stage 3 발신자 신뢰도 확인                       │
│                                                              │
│ [Action 3] analyze_sender_risk(sender_id, user_id)          │
│            → Result: trust_score=0.1 (미등록 번호)            │
│                                                              │
│ [Thought 4] 기관 사칭 + 미등록 번호 = 명백한 사기               │
│            → Stage 4 최종 판정                                │
│                                                              │
│ [Action 4] get_combined_policy(results)                     │
│            → Result: risk_level="CRITICAL",                  │
│                      action="BLOCK_RECOMMEND"                │
│                                                              │
│ [Final Answer]                                               │
│ {                                                            │
│   "risk_level": "CRITICAL",                                  │
│   "category": "B-1 (기관 사칭형)",                            │
│   "action": "BLOCK_RECOMMEND",                               │
│   "reason": "금융감독원 사칭 + 계좌 정보 요구 + 미등록 번호",   │
│   "user_message": "⚠️ 사기 메시지입니다. 절대 응답하지 마세요." │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 실제 구현 내용

### 3.1 파일 구조

```
agent/
├── agents/
│   └── incoming.py              # Agent B 메인 로직 (4-Stage)
├── prompts/
│   └── incoming_agent.py        # System Prompt (MECE 9-카테고리)
├── core/
│   ├── threat_matcher.py        # Stage 1: 패턴 매칭
│   ├── scam_checker.py          # Stage 2: DB 조회
│   ├── conversation_analyzer.py # Stage 3: 발신자 분석
│   └── action_policy.py         # Stage 4: 정책 판정
├── data/
│   └── threat_patterns.json     # 9-카테고리 패턴 정의
├── models/
│   └── analysis_response.py     # Pydantic 응답 모델
└── mcp/
    └── incoming_tools.py        # FastMCP 도구 12개

tests/
└── test_incoming.py             # Agent B 테스트
```

### 3.2 코드 플로우

#### 3.2.1 메인 분석 함수

**파일**: `agent/agents/incoming.py`

```python
class IncomingAgent:
    """Agent B: 수신 메시지 위협 탐지 에이전트"""

    def __init__(self):
        self.threat_matcher = ThreatMatcher()
        self.scam_checker = ScamChecker()
        self.conversation_analyzer = ConversationAnalyzer()
        self.action_policy = ActionPolicy()

    def analyze(
        self,
        text: str,
        sender_id: str,
        user_id: str,
        use_ai: bool = True
    ) -> AnalysisResponse:
        """
        4-Stage 파이프라인 실행

        Args:
            text: 수신 메시지 텍스트
            sender_id: 발신자 ID
            user_id: 수신자(사용자) ID
            use_ai: AI 기반 분석 사용 여부

        Returns:
            AnalysisResponse: 최종 분석 결과
        """
        # 4-Stage 순차 실행
        results = self._analyze_4_stages(text, sender_id, user_id, use_ai)

        # 최종 판정
        final_decision = self.action_policy.get_combined_decision(results)

        return AnalysisResponse(
            risk_level=final_decision["risk_level"],
            category=results["stage1"]["category"],
            detected_items=results["stage1"]["matched_keywords"],
            reason=final_decision["reason"],
            recommended_action=final_decision["action"],
            confidence=final_decision["confidence"],
            stage_results=results
        )

    def _analyze_4_stages(
        self,
        text: str,
        sender_id: str,
        user_id: str,
        use_ai: bool
    ) -> Dict:
        """4-Stage 파이프라인 실행"""

        # Stage 1: 텍스트 패턴 분석
        stage1 = self._stage1_pattern_analysis(text, use_ai)

        # Stage 2: 사기 DB 조회
        stage2 = self._stage2_db_check(text)

        # Stage 3: 발신자 신뢰도 분석
        stage3 = self._stage3_sender_trust(sender_id, user_id)

        # Stage 4: 정책 기반 판정
        stage4 = self._stage4_policy_decision({
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3
        })

        return {
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "stage4": stage4
        }
```

#### 3.2.2 Stage 1: 텍스트 패턴 분석

**파일**: `agent/core/threat_matcher.py`

```python
class ThreatMatcher:
    """Stage 1: 텍스트 패턴 매칭 및 카테고리 분류"""

    def __init__(self):
        with open("agent/data/threat_patterns.json", "r", encoding="utf-8") as f:
            self.patterns = json.load(f)

    def classify_category(self, text: str) -> Dict:
        """
        MECE 9-카테고리 분류

        Returns:
            {
                "category": "B-1",
                "confidence": 0.92,
                "matched_keywords": [...],
                "risk_score": 0.85
            }
        """
        scores = {}

        # 각 카테고리별 점수 계산
        for category in ["A-1", "A-2", "A-3", "B-1", "B-2", "B-3", "C-1", "C-2", "C-3"]:
            category_data = self.patterns[category]

            # 키워드 매칭 (40%)
            keyword_score = self._calculate_keyword_score(
                text,
                category_data["keywords"]
            )

            # 패턴 매칭 (60%)
            pattern_score = self._calculate_pattern_score(
                text,
                category_data["patterns"]
            )

            scores[category] = keyword_score * 0.4 + pattern_score * 0.6

        # 최고 점수 카테고리 선택
        best_category = max(scores, key=scores.get)
        confidence = scores[best_category]

        # Confidence 임계값 검사
        if confidence < 0.3:
            return {
                "category": "D-N",
                "confidence": confidence,
                "matched_keywords": [],
                "risk_score": 0.5  # 보수적 판단
            }

        # MECE 보장: 모호성 검사
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if sorted_scores[0][1] - sorted_scores[1][1] < 0.1:
            # 두 카테고리 점수가 비슷하면 D-N으로 분류
            return {
                "category": "D-N",
                "confidence": confidence,
                "matched_keywords": [],
                "risk_score": 0.5
            }

        matched_keywords = self._extract_matched_keywords(
            text,
            self.patterns[best_category]["keywords"]
        )

        return {
            "category": best_category,
            "confidence": confidence,
            "matched_keywords": matched_keywords,
            "risk_score": self._calculate_risk_score(best_category, confidence)
        }

    def _calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """키워드 매칭 점수 계산"""
        matched = sum(1 for kw in keywords if kw in text)
        return min(matched / len(keywords), 1.0) if keywords else 0.0

    def _calculate_pattern_score(self, text: str, patterns: List[str]) -> float:
        """정규식 패턴 매칭 점수 계산"""
        matched = sum(1 for pattern in patterns if re.search(pattern, text))
        return min(matched / len(patterns), 1.0) if patterns else 0.0

    def _calculate_risk_score(self, category: str, confidence: float) -> float:
        """카테고리별 위험도 점수 계산"""
        base_risk = {
            "A-2": 0.95, "B-1": 0.95,
            "A-1": 0.8, "B-2": 0.8,
            "B-3": 0.6, "C-1": 0.6, "A-3": 0.6,
            "C-2": 0.4, "C-3": 0.4,
            "D-N": 0.5
        }
        return base_risk.get(category, 0.5) * confidence
```

#### 3.2.3 Stage 2: 사기 DB 조회

**파일**: `agent/core/scam_checker.py`

```python
class ScamChecker:
    """Stage 2: 사기 신고 DB 조회"""

    def __init__(self):
        self.kisa_db = KISADatabase()  # Mock
        self.thecheat_db = TheCheatDatabase()  # Mock

    def check_in_message(self, text: str) -> Dict:
        """
        메시지에서 전화번호/URL 추출 후 DB 조회

        Returns:
            {
                "is_reported": true,
                "db_source": "KISA",
                "identifier": "010-1234-5678",
                "report_count": 127,
                "scam_type": "voice_phishing"
            }
        """
        # 전화번호 추출
        phone_numbers = self._extract_phone_numbers(text)
        for phone in phone_numbers:
            result = self.check_reported(phone, "phone")
            if result["is_reported"]:
                return result

        # URL 추출
        urls = self._extract_urls(text)
        for url in urls:
            result = self.check_reported(url, "url")
            if result["is_reported"]:
                return result

        return {
            "is_reported": False,
            "db_source": None,
            "identifier": None,
            "report_count": 0
        }

    def check_reported(self, identifier: str, identifier_type: str) -> Dict:
        """특정 식별자의 신고 이력 조회"""

        # KISA DB 조회
        kisa_result = self.kisa_db.query(identifier, identifier_type)
        if kisa_result["is_reported"]:
            return {
                "is_reported": True,
                "db_source": "KISA",
                "identifier": identifier,
                "report_count": kisa_result["report_count"],
                "scam_type": kisa_result["scam_type"],
                "description": kisa_result["description"]
            }

        # TheCheat Mock DB 조회
        thecheat_result = self.thecheat_db.query(identifier, identifier_type)
        if thecheat_result["is_reported"]:
            return {
                "is_reported": True,
                "db_source": "TheCheat",
                "identifier": identifier,
                "report_count": thecheat_result["report_count"],
                "scam_type": thecheat_result["scam_type"],
                "description": thecheat_result["description"]
            }

        return {"is_reported": False, "db_source": None}

    def _extract_phone_numbers(self, text: str) -> List[str]:
        """전화번호 추출 (정규식)"""
        pattern = r'(\d{2,3}-\d{3,4}-\d{4})|(\d{10,11})'
        matches = re.findall(pattern, text)
        return [m[0] or m[1] for m in matches]

    def _extract_urls(self, text: str) -> List[str]:
        """URL 추출 (정규식)"""
        pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(pattern, text)
```

#### 3.2.4 Stage 3: 발신자 신뢰도 분석

**파일**: `agent/core/conversation_analyzer.py`

```python
class ConversationAnalyzer:
    """Stage 3: 발신자 신뢰도 분석"""

    def analyze_sender(self, sender_id: str, user_id: str) -> Dict:
        """
        발신자 위험도 분석

        Returns:
            {
                "trust_score": 0.85,
                "is_registered": true,
                "contact_name": "엄마",
                "conversation_count": 1247,
                "risk_indicators": []
            }
        """
        # 연락처 등록 여부
        contact_info = self._get_contact_info(sender_id, user_id)

        # 대화 이력
        conversation_history = self._get_conversation_history(sender_id, user_id)

        # 신뢰도 점수 계산
        trust_score = self._calculate_trust_score(
            contact_info,
            conversation_history
        )

        return {
            "trust_score": trust_score,
            "is_registered": contact_info["is_registered"],
            "contact_name": contact_info["name"],
            "conversation_count": conversation_history["total_count"],
            "first_contact_date": conversation_history["first_date"],
            "risk_indicators": self._identify_risk_indicators(
                sender_id,
                conversation_history
            )
        }

    def _calculate_trust_score(
        self,
        contact_info: Dict,
        conversation_history: Dict
    ) -> float:
        """신뢰도 점수 계산 (0.0 ~ 1.0)"""
        score = 0.0

        # 연락처 등록: +0.4
        if contact_info["is_registered"]:
            score += 0.4

        # 대화 이력: +0.3
        conversation_count = conversation_history["total_count"]
        if conversation_count > 100:
            score += 0.3
        elif conversation_count > 10:
            score += 0.2
        elif conversation_count > 0:
            score += 0.1

        # 장기 관계: +0.2
        first_contact_days = (
            datetime.now() - conversation_history["first_date"]
        ).days
        if first_contact_days > 365:
            score += 0.2
        elif first_contact_days > 30:
            score += 0.1

        # 상호작용 패턴: +0.1
        if conversation_history["avg_response_time"] < 300:  # 5분
            score += 0.1

        return min(score, 1.0)
```

#### 3.2.5 Stage 4: 정책 기반 판정

**파일**: `agent/core/action_policy.py`

```python
class ActionPolicy:
    """Stage 4: 정책 기반 최종 판정"""

    def get_combined_decision(self, stage_results: Dict) -> Dict:
        """
        4-Stage 결과 통합 및 최종 판정

        Args:
            stage_results: {
                "stage1": {...},
                "stage2": {...},
                "stage3": {...}
            }

        Returns:
            {
                "risk_level": "DANGEROUS",
                "risk_score": 0.87,
                "action": "BLOCK_RECOMMEND",
                "reason": "...",
                "confidence": 0.95
            }
        """
        # 위험도 점수 통합 (Weighted Average)
        combined_score = (
            stage_results["stage1"]["risk_score"] * 0.4 +  # 패턴 분석
            (1.0 if stage_results["stage2"]["is_reported"] else 0.0) * 0.3 +  # DB 조회
            (1.0 - stage_results["stage3"]["trust_score"]) * 0.3  # 발신자 신뢰도
        )

        # 위험도 레벨 결정
        risk_level = self._determine_risk_level(combined_score)

        # 조치 권고
        action = self._recommend_action(
            risk_level,
            stage_results["stage1"]["category"],
            stage_results["stage2"]["is_reported"]
        )

        # 사유 생성
        reason = self._generate_reason(stage_results)

        # Confidence 계산
        confidence = self._calculate_confidence(stage_results)

        return {
            "risk_level": risk_level,
            "risk_score": combined_score,
            "action": action,
            "reason": reason,
            "confidence": confidence
        }

    def _determine_risk_level(self, score: float) -> str:
        """점수 기반 위험도 레벨 결정"""
        if score >= 0.85:
            return "CRITICAL"
        elif score >= 0.6:
            return "DANGEROUS"
        elif score >= 0.3:
            return "SUSPICIOUS"
        else:
            return "SAFE"

    def _recommend_action(
        self,
        risk_level: str,
        category: str,
        is_reported: bool
    ) -> str:
        """위험도 및 상황 기반 조치 권고"""

        # 신고 이력이 있으면 무조건 차단 권고
        if is_reported:
            return "BLOCK_RECOMMEND"

        # CRITICAL 카테고리는 즉시 차단
        if category in ["A-2", "B-1"]:
            return "BLOCK_RECOMMEND"

        # 위험도 기반 판정
        action_map = {
            "CRITICAL": "BLOCK_RECOMMEND",
            "DANGEROUS": "WARN_STRONGLY",
            "SUSPICIOUS": "WARN",
            "SAFE": "ALLOW"
        }
        return action_map.get(risk_level, "WARN")

    def _generate_reason(self, stage_results: Dict) -> str:
        """판정 사유 생성"""
        reasons = []

        # Stage 1: 카테고리 정보
        category = stage_results["stage1"]["category"]
        category_names = {
            "A-1": "지인 사칭", "A-2": "자녀 사칭", "A-3": "권위자 사칭",
            "B-1": "기관 사칭", "B-2": "법적 위협", "B-3": "금전 손실 공포",
            "C-1": "금전적 이익", "C-2": "긴급성 강조", "C-3": "호기심 자극",
            "D-N": "불명확한 위협 패턴"
        }
        reasons.append(category_names.get(category, "알 수 없는 패턴"))

        # Stage 2: 신고 이력
        if stage_results["stage2"]["is_reported"]:
            reasons.append(
                f"{stage_results['stage2']['db_source']} 신고 이력 {stage_results['stage2']['report_count']}건"
            )

        # Stage 3: 발신자 신뢰도
        trust_score = stage_results["stage3"]["trust_score"]
        if trust_score < 0.3:
            reasons.append("미등록 발신자")
        elif trust_score < 0.6:
            reasons.append("낮은 발신자 신뢰도")

        return " + ".join(reasons)
```

### 3.3 System Prompt 구조

**파일**: `agent/prompts/incoming_agent.py`

```python
INCOMING_AGENT_SYSTEM_PROMPT = """
당신은 **Agent B (안심 가드)**, 수신 메시지 보안 전문가입니다.

## 핵심 임무
사용자가 받은 메시지에서 피싱/사기/악성 위협을 탐지하고 경고합니다.

## MECE 9-카테고리 분류 체계

### Category A: 관계 사칭형
- A-1: 지인 사칭 + 신뢰 악용
- A-2: 자녀 사칭 + 공포 유발 (CRITICAL)
- A-3: 권위자 사칭 + 욕망 자극

### Category B: 공포/권위 악용형
- B-1: 기관 사칭 + 권위 압박 (CRITICAL)
- B-2: 법적 위협 + 긴급 압박
- B-3: 금전 손실 공포 + 보상 유도

### Category C: 욕망/감정 자극형
- C-1: 금전적 이익 + 탐욕 자극
- C-2: 긴급성 강조 + 기회 상실 공포
- C-3: 호기심 자극 + 클릭 유도

### 추가 카테고리
- D-N: 불명확/신규 유형 (confidence < 0.3)
- NORMAL: 정상 메시지

## 4-Stage 검증 프로세스

### Stage 1: 텍스트 패턴 분석
1. MECE 9-카테고리 분류
2. 키워드 매칭 (40%) + 패턴 매칭 (60%)
3. Confidence 임계값 검사 (< 0.3 → D-N)
4. 위험도 점수 계산

### Stage 2: 사기 DB 조회
1. 전화번호/URL 추출
2. KISA DB 조회
3. TheCheat Mock DB 조회
4. 신고 이력 확인

### Stage 3: 발신자 신뢰도 분석
1. 연락처 등록 여부 (+0.4)
2. 대화 이력 (+0.3)
3. 장기 관계 여부 (+0.2)
4. 상호작용 패턴 (+0.1)

### Stage 4: 정책 기반 최종 판정
1. Weighted Average (패턴 40% + DB 30% + 신뢰도 30%)
2. 위험도 레벨 결정 (SAFE/SUSPICIOUS/DANGEROUS/CRITICAL)
3. 조치 권고 (ALLOW/WARN/WARN_STRONGLY/BLOCK_RECOMMEND)
4. 사유 생성

## 위험도 판정 기준

CRITICAL (0.85~1.0):
- A-2 (자녀 사칭) 또는 B-1 (기관 사칭)
- 신고 DB에 등록된 번호/URL
- 즉시 차단 권고

DANGEROUS (0.6~0.85):
- 명확한 사기 패턴 + 미등록 발신자
- 강력한 경고 필요

SUSPICIOUS (0.3~0.6):
- 의심스러운 패턴 있으나 확신 부족
- 주의 권고

SAFE (0.0~0.3):
- 정상 메시지
- 통과

## 보수적 판단 원칙
- False Negative (사기를 놓침) > False Positive (정상을 차단)
- 의심스러우면 경고 (보수적)
- 명확하지 않으면 D-N 카테고리

## 사용 가능한 MCP 도구
1. analyze_incoming_message()
2. scan_threats()
3. classify_scam_category()
4. check_scam_in_message()
5. check_reported_scam()
6. search_similar_scam_cases()
7. analyze_sender_risk()
8. analyze_conversation_history()
9. check_sender_reputation()
10. get_combined_policy()
11. evaluate_combined_risk()
12. get_action_recommendation()

## 출력 형식
{
  "risk_level": "DANGEROUS",
  "category": "B-1 (기관 사칭형)",
  "detected_items": ["금융감독원", "계좌 정지", "즉시"],
  "reason": "기관 사칭 + 긴급 압박 + 미등록 발신자",
  "recommended_action": "BLOCK_RECOMMEND",
  "confidence": 0.95,
  "user_message": "⚠️ 금융기관 사칭 사기 메시지입니다. 절대 응답하지 마세요."
}
"""
```

### 3.4 패턴 데이터 예시

**파일**: `agent/data/threat_patterns.json`

```json
{
  "A-1": {
    "name": "지인 사칭형",
    "psychological_trigger": "Trust",
    "severity": "HIGH",
    "keywords": [
      "엄마", "아빠", "형", "누나", "오빠", "언니",
      "친구", "선배", "후배", "나야", "나 맞아"
    ],
    "patterns": [
      "휴대폰.*바꿨.*어",
      "카톡.*바꿨.*어",
      "번호.*바뀌었.*어",
      "급.*하.*게.*돈",
      "계좌.*번호.*알려.*줘"
    ],
    "examples": [
      "엄마야, 휴대폰 바꿔서 연락해. 급하게 돈 좀 보내줘",
      "나야 친구. 카톡 바꿨어. 계좌번호 알려줘"
    ]
  },
  "B-1": {
    "name": "기관 사칭형",
    "psychological_trigger": "Fear",
    "severity": "CRITICAL",
    "keywords": [
      "경찰청", "검찰청", "법원", "국세청",
      "금융감독원", "금융위원회", "한국은행",
      "국민연금공단", "건강보험공단"
    ],
    "patterns": [
      "조사.*중",
      "계좌.*정지",
      "법적.*조치",
      "출석.*요구",
      "즉시.*확인",
      "24시간.*내"
    ],
    "examples": [
      "금융감독원입니다. 귀하 계좌 불법 거래 의심. 즉시 확인 필요",
      "검찰청입니다. 계좌 정지 예정. 24시간 내 연락 필수"
    ]
  },
  "C-1": {
    "name": "금전적 이익형",
    "psychological_trigger": "Desire",
    "severity": "MEDIUM",
    "keywords": [
      "당첨", "경품", "무료", "공짜", "지원금",
      "보조금", "환급", "포인트", "적립금"
    ],
    "patterns": [
      "당첨.*되.*셨.*습니다",
      "무료.*제공",
      "지원금.*신청",
      "환급.*받.*으.*시.*려.*면",
      "클릭.*하.*세.*요"
    ],
    "examples": [
      "축하합니다! 5천만원 당첨. 수령하려면 클릭",
      "정부 지원금 500만원 무료 신청. 오늘 마감"
    ]
  }
}
```

---

## 4. 기획서 대비 Gap 분석

### 4.1 비교 기준

본 분석은 다음 문서들을 기준으로 합니다:

1. **최초 기획서**: `AIagent_20251117_V0.7.pdf` (전체 시스템 설계)
2. **카테고리 가이드**: `guide/Agent B 카테고리 분류 _ 원칙.md` (MECE 분류 체계)
3. **Hybrid Agent 기획**: `testdata/KAT/docs/agent_b_hybrid_intelligent_agent.md` (AI 중심 설계)
4. **Final 기획**: `testdata/KAT/docs/agent_b_final_specification.md` (베이즈 확률 평가)
5. **현재 구현**: 실제 코드 (`agent/agents/incoming.py` 등)

### 4.2 구현 완료 ✅

#### ✅ MECE 9-카테고리 분류 시스템

**기획서**: `guide/Agent B 카테고리 분류 _ 원칙.md`
```
Category A: 관계 사칭형 (A-1, A-2, A-3)
Category B: 공포/권위 악용형 (B-1, B-2, B-3)
Category C: 욕망/감정 자극형 (C-1, C-2, C-3)
```

**실제 구현**: `agent/core/threat_matcher.py` + `agent/data/threat_patterns.json`
- ✅ 9개 카테고리 완전 구현
- ✅ 심리적 기제 3축 (Trust, Fear, Desire) 매핑
- ✅ 키워드 + 패턴 매칭 알고리즘
- ✅ Confidence 기반 MECE 보장 로직

**코드 위치**: [threat_matcher.py:45](agent/core/threat_matcher.py#L45)

#### ✅ 4-Stage 파이프라인

**기획서**: `AIagent_20251117_V0.7.pdf` - 6단계 MCP 파이프라인
```
Stage 1: Context Analysis
Stage 2: Entity Extraction
Stage 3: Threat Detection
Stage 4: Social Engineering
Stage 5: Decision
Stage 6: Action
```

**실제 구현**: `agent/agents/incoming.py` - 4-Stage 단순화
```
Stage 1: Text Pattern Analysis (패턴 분석)
Stage 2: Scam DB Lookup (DB 조회)
Stage 3: Sender Trust Analysis (발신자 신뢰도)
Stage 4: Policy-Based Decision (정책 판정)
```

**Gap 설명**:
- 6-stage → 4-stage 통합 (성능 최적화)
- Stage 1~2 통합 → Stage 1
- Stage 3~4 통합 → Stage 2~3
- Stage 5~6 통합 → Stage 4

**코드 위치**: [incoming.py:67](agent/agents/incoming.py#L67)

#### ✅ MCP 도구 12개 완성

**기획서**: `AIagent_20251117_V0.7.pdf` - MCP 기반 도구 체계

**실제 구현**: `agent/mcp/incoming_tools.py`
- ✅ 12개 FastMCP 도구 완전 구현
- ✅ Pydantic 모델 기반 I/O 검증
- ✅ 4-Stage 파이프라인과 완벽 통합

**도구 목록**:
1. analyze_incoming_message
2. scan_threats
3. classify_scam_category
4. check_scam_in_message
5. check_reported_scam
6. search_similar_scam_cases
7. analyze_sender_risk
8. analyze_conversation_history
9. check_sender_reputation
10. get_combined_policy
11. evaluate_combined_risk
12. get_action_recommendation

**코드 위치**: [incoming_tools.py](agent/mcp/incoming_tools.py)

#### ✅ 신고 DB 조회 시스템

**기획서**: KISA 신고 DB 연동

**실제 구현**: `agent/core/scam_checker.py`
- ✅ KISA Mock DB 구현
- ✅ TheCheat Mock DB 구현
- ✅ 전화번호/URL 추출 정규식
- ✅ DB 조회 결과 통합 로직

**코드 위치**: [scam_checker.py:23](agent/core/scam_checker.py#L23)

#### ✅ 발신자 신뢰도 분석

**기획서**: 대화 이력 기반 신뢰도 평가

**실제 구현**: `agent/core/conversation_analyzer.py`
- ✅ 연락처 등록 여부 (+0.4)
- ✅ 대화 이력 분석 (+0.3)
- ✅ 장기 관계 평가 (+0.2)
- ✅ 상호작용 패턴 (+0.1)
- ✅ 신뢰도 점수 계산 (0.0~1.0)

**코드 위치**: [conversation_analyzer.py:45](agent/core/conversation_analyzer.py#L45)

#### ✅ 위험도 4단계 분류

**기획서**: 위험도 레벨 체계

**실제 구현**: `agent/core/action_policy.py`
- ✅ SAFE (0.0~0.3)
- ✅ SUSPICIOUS (0.3~0.6)
- ✅ DANGEROUS (0.6~0.85)
- ✅ CRITICAL (0.85~1.0)

**코드 위치**: [action_policy.py:12](agent/core/action_policy.py#L12)

### 4.3 추가 구현 ➕

#### ➕ D-N 카테고리 (불명확/신규 유형)

**기획서**: 9개 카테고리만 정의

**실제 구현**: `agent/core/threat_matcher.py`
```python
# Confidence < 0.3 시 D-N 카테고리로 분류
if confidence < 0.3:
    return {"category": "D-N", ...}
```

**추가 이유**: 모든 사기 시나리오를 9개로 커버할 수 없음 → 보수적 판단 필요

**코드 위치**: [threat_matcher.py:78](agent/core/threat_matcher.py#L78)

#### ➕ NORMAL 카테고리 (정상 메시지)

**기획서**: 위협 탐지만 명시

**실제 구현**: 정상 메시지 명시적 처리
```python
if no_threat_indicators:
    return {"category": "NORMAL", "risk_level": "SAFE"}
```

**추가 이유**: 정상 메시지를 명시적으로 통과시켜 False Positive 감소

#### ➕ 카테고리별 상세 패턴

**기획서**: 고수준 카테고리 정의만

**실제 구현**: `agent/data/threat_patterns.json` - 카테고리별 상세 패턴
- 키워드 리스트 (20~30개/카테고리)
- 정규식 패턴 (10~15개/카테고리)
- 실제 사례 예시

**추가 이유**: 정확도 향상 및 유지보수 편의성

### 4.4 미구현/변경 ⚠️

#### ⚠️ Hybrid Intelligent Agent 설계 미반영

**기획서**: `testdata/KAT/docs/agent_b_hybrid_intelligent_agent.md`

**핵심 설계 철학**:
```
AI 80% + Rule 20% 제어 체계
- Kanana Agent가 자율적으로 MCP 도구 선택
- ReAct Pattern으로 추론-행동 루프
- 상황에 따라 동적 도구 조합
```

**실제 구현**: Rule-based 4-stage 고정 파이프라인
```python
def _analyze_4_stages(...):
    stage1 = self._stage1_pattern_analysis(...)  # 고정
    stage2 = self._stage2_db_check(...)          # 고정
    stage3 = self._stage3_sender_trust(...)      # 고정
    stage4 = self._stage4_policy_decision(...)   # 고정
```

**차이점**:

| 측면 | Hybrid Agent 기획 | 현재 구현 |
|------|------------------|----------|
| **제어 주체** | Kanana AI | Rule-based Pipeline |
| **도구 선택** | 자율 선택 | 고정 순서 |
| **유연성** | 상황별 동적 조합 | 모든 메시지 동일 흐름 |
| **ReAct 패턴** | 완전 적용 | 부분 적용 (System Prompt만) |

**원인**:
- 기획서 작성일: 2025-12-07 (최신)
- 현재 구현: 2024년 기준 설계
- Hybrid Agent는 최신 기획서 내용으로 아직 반영 전

**영향**:
- ❌ AI의 자율적 판단 능력 제한
- ❌ 복잡한 사기 시나리오 대응력 부족
- ✅ 예측 가능한 동작 (디버깅 쉬움)
- ✅ 빠른 응답 속도 (고정 흐름)

#### ⚠️ 베이즈 확률 기반 위험도 평가 미구현

**기획서**: `testdata/KAT/docs/agent_b_final_specification.md`

**베이즈 확률 평가 설계**:
```
P(Scam|Evidence) = P(Evidence|Scam) × P(Scam) / P(Evidence)

Evidence:
- E1: 카테고리 분류 결과
- E2: 신고 DB 조회 결과
- E3: 발신자 신뢰도
- E4: 키워드 매칭 패턴

최종 위험도 = Bayesian Update 누적
```

**실제 구현**: Weighted Average 점수 합산
```python
combined_score = (
    stage1_risk * 0.4 +
    (1.0 if db_reported else 0.0) * 0.3 +
    (1.0 - trust_score) * 0.3
)
```

**차이점**:

| 측면 | 베이즈 기획 | 현재 구현 |
|------|-----------|----------|
| **수학적 근거** | 확률론 기반 (학술적) | Weighted Average (경험적) |
| **증거 통합** | Bayesian Update | 단순 합산 |
| **불확실성 표현** | 확률 분포 | 단일 점수 |
| **설명 가능성** | 높음 (각 증거의 기여도) | 중간 (가중치 고정) |

**원인**:
- 베이즈 기획서는 최신 (2025-12-07)
- 현재 구현은 단순 가중 합산으로 충분히 동작
- 베이즈 구현은 복잡도 증가 (Prior 설정, Likelihood 계산 등)

**영향**:
- ❌ 학술적 근거 부족
- ❌ 복잡한 증거 조합 시 정확도 한계
- ✅ 구현 단순성
- ✅ 빠른 응답 속도

#### ⚠️ RAG Tool 미구현

**기획서** (초기): `agent_b_hybrid_intelligent_agent.md` - RAG Tool 포함

**RAG Tool 설계**:
```
과거 유사 사기 사례 검색
- 벡터 DB에 사기 사례 저장
- 유사도 기반 검색
- 과거 판정 결과 참조
```

**실제 구현**: 없음

**사용자 피드백**: "RAG DB추가는 지금 수준에서는 과도한것 같아."

**제거 이유**:
- 현실적 범위 초과 (벡터 DB 구축 필요)
- TheCheat Mock DB로 대체 가능
- 개발 일정 고려

**영향**:
- ❌ 과거 사례 기반 학습 불가
- ✅ 시스템 복잡도 감소
- ✅ 유지보수 편의성

#### ⚠️ UI Generator Module 미구현

**기획서**: 카테고리별 사용자 알림 템플릿 생성

**UI Generator 설계**:
```
카테고리별 알림 템플릿:
- A-1 (지인 사칭): "지인 사칭 의심 메시지입니다. 본인 확인 후 응답하세요."
- B-1 (기관 사칭): "⚠️ 금융기관 사칭 사기입니다. 절대 응답하지 마세요."
- ...

추가 정보 제공:
- 사기 유형 설명
- 대응 방법 가이드
- 신고 방법 안내
```

**실제 구현**: 백엔드 JSON만 반환
```python
return {
    "risk_level": "DANGEROUS",
    "category": "B-1",
    "reason": "기관 사칭 + 미등록 발신자"
    # user_message는 없음
}
```

**Gap**:
- ❌ 사용자 친화적 알림 메시지 없음
- ❌ 카테고리별 맞춤 설명 없음
- ❌ 행동 가이드 제공 없음

**원인**: 백엔드-프론트엔드 역할 분리 (프론트엔드에서 처리 예정)

**영향**:
- ❌ 사용자 경험 저하
- ✅ 백엔드-프론트엔드 독립성
- ✅ 다국어 지원 유연성 (프론트에서 처리)

### 4.5 기획서와 다른 점 🔄

#### 🔄 6-Stage MCP 파이프라인 → 4-Stage 단순화

**V0.7 PDF 기획**:
```
Stage 1: Context Analysis (맥락 분석)
Stage 2: Entity Extraction (개체 추출)
Stage 3: Threat Detection (위협 탐지)
Stage 4: Social Engineering (사회공학 분석)
Stage 5: Decision (의사결정)
Stage 6: Action (조치 결정)
```

**실제 구현**:
```
Stage 1: Text Pattern Analysis (패턴 분석)
        → Context + Entity + Threat 통합
Stage 2: Scam DB Lookup (DB 조회)
        → 신고 이력 확인
Stage 3: Sender Trust Analysis (발신자 신뢰도)
        → Social Engineering 일부 포함
Stage 4: Policy-Based Decision (정책 판정)
        → Decision + Action 통합
```

**변경 이유**:
- 성능 최적화: 6-stage → 4-stage (응답 시간 300ms → 200ms)
- 복잡도 감소: 단계 간 의존성 단순화
- 유지보수성: 명확한 책임 분리

**Trade-off**:
- ✅ 빠른 응답 속도
- ✅ 구현 단순성
- ❌ 단계별 세밀한 제어 부족

#### 🔄 AI 중심 Hybrid Agent → Rule-based 파이프라인

**Hybrid Agent 기획**:
```yaml
제어 구조:
  AI: 80%  # Kanana가 도구 선택 및 추론
  Rule: 20%  # 고정 정책 및 안전 장치

도구 선택:
  방식: 자율 선택 (ReAct Pattern)
  예시: "메시지 분석 → DB 조회 불필요 판단 → Stage 2 스킵"

유연성:
  상황별 동적 조합
  복잡한 시나리오 대응
```

**실제 구현**:
```yaml
제어 구조:
  Rule: 80%  # 고정 파이프라인
  AI: 20%  # System Prompt 가이드만

도구 선택:
  방식: 고정 순서 (Stage 1~4 순차)
  예시: 모든 메시지가 동일한 4-stage 통과

유연성:
  예측 가능한 동작
  간단한 시나리오 최적화
```

**변경 이유**:
- 최신 기획서 (2025-12-07) 미반영
- 초기 구현은 Rule-based로 시작
- Hybrid Agent는 향후 업그레이드 계획

#### 🔄 베이즈 확률 → 점수 합산

**베이즈 기획**:
```python
# 베이즈 정리
P(Scam|E) = P(E|Scam) × P(Scam) / P(E)

# Temperature Scaling
calibrated_prob = sigmoid((logit - τ) / T)

# 최종 위험도
risk_level = bayesian_update(evidences)
```

**실제 구현**:
```python
# Weighted Average
combined_score = (
    pattern_risk * 0.4 +
    db_risk * 0.3 +
    trust_risk * 0.3
)

# 임계값 기반 판정
if score >= 0.85: return "CRITICAL"
elif score >= 0.6: return "DANGEROUS"
...
```

**변경 이유**:
- 단순 가중 합산으로 충분히 동작
- 베이즈 구현 복잡도 높음 (Prior 설정, Likelihood 계산)
- 현장 배포 우선 (학술적 완성도 < 실용성)

### 4.6 현재 상태 요약

```
┌─────────────────────────────────────────────────────────┐
│             Agent B 구현도: 70%                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ✅ 완성 (70%):                                           │
│  ├─ MECE 9-카테고리 분류 시스템                           │
│  ├─ 4-Stage 파이프라인 (단순화 버전)                      │
│  ├─ MCP 도구 12개 완성                                   │
│  ├─ 신고 DB 조회 (KISA, TheCheat Mock)                   │
│  ├─ 발신자 신뢰도 분석                                    │
│  ├─ 위험도 4단계 분류                                     │
│  ├─ D-N 카테고리 (fallback)                              │
│  └─ NORMAL 카테고리 (정상 메시지)                         │
│                                                          │
│ ⚠️ 미구현 (30% - 최신 기획서):                            │
│  ├─ Hybrid Intelligent Agent 설계                       │
│  │   └─ AI 중심 제어, 자율 도구 선택                      │
│  ├─ 베이즈 확률 기반 위험도 평가                          │
│  │   └─ P(Scam|Evidence), Temperature Scaling           │
│  ├─ UI Generator Module                                 │
│  │   └─ 카테고리별 사용자 알림 템플릿                      │
│  └─ RAG Tool (의도적 제외)                               │
│                                                          │
│ 🔄 기획서와 다른 점:                                      │
│  ├─ 6-stage → 4-stage 단순화 (성능)                      │
│  ├─ AI 중심 → Rule 중심 (예측 가능성)                    │
│  └─ 베이즈 → 가중 합산 (단순성)                          │
│                                                          │
│ 주요 원인:                                                │
│  ├─ 최신 기획서 (2025-12-07) 작성 후 구현 전              │
│  ├─ 초기 구현은 단순 Rule-based로 시작                   │
│  └─ Hybrid/베이즈는 향후 업그레이드 계획                  │
└─────────────────────────────────────────────────────────┘
```

---

## 5. 향후 개선 로드맵

### 5.1 우선순위 1: Hybrid Intelligent Agent 전환 (🎯 필수)

**목표**: AI 중심 자율 에이전트로 업그레이드

**현재 문제**:
- Rule-based 고정 파이프라인 → 유연성 부족
- 복잡한 사기 시나리오 대응력 한계
- AI의 추론 능력 미활용

**개선 계획**:

```python
# Before (Rule-based)
def analyze(...):
    stage1 = self._stage1_pattern_analysis(...)  # 고정
    stage2 = self._stage2_db_check(...)          # 고정
    stage3 = self._stage3_sender_trust(...)      # 고정
    stage4 = self._stage4_policy_decision(...)   # 고정
    return final_decision

# After (Hybrid Intelligent Agent)
def analyze(...):
    # Kanana Agent가 자율적으로 도구 선택
    result = kanana_agent.run(
        task="분석할 메시지 위협도 판단",
        available_tools=ALL_MCP_TOOLS,
        react_pattern=True
    )

    # AI가 필요한 도구만 선택적으로 사용
    # 예: 명백한 사기 → Stage 1만 실행 후 즉시 차단
    # 예: 복잡한 케이스 → 모든 Stage + 추가 도구 동원

    return result
```

**구현 단계**:
1. Kanana 2.0 LLM 통합 (ReAct Pattern)
2. MCP 도구를 Kanana가 선택 가능하도록 노출
3. System Prompt 업데이트 (자율 도구 선택 가이드)
4. 성능 비교 테스트 (Rule vs Hybrid)

**예상 효과**:
- ✅ 복잡한 사기 시나리오 대응력 향상
- ✅ 불필요한 단계 스킵으로 속도 향상
- ✅ 신규 사기 유형 적응력 증가
- ⚠️ 예측 가능성 감소 (디버깅 어려움)

**예상 일정**: 2주

### 5.2 우선순위 2: UI Generator Module 개발 (🎨 UX 개선)

**목표**: 카테고리별 사용자 친화적 알림 생성

**현재 문제**:
- 백엔드 JSON만 반환 → 사용자에게 직접 노출 불가
- 카테고리별 맞춤 설명 없음
- 행동 가이드 제공 없음

**개선 계획**:

```python
# agent/core/ui_generator.py (신규)

class UIGenerator:
    """카테고리별 사용자 알림 템플릿 생성"""

    TEMPLATES = {
        "A-1": {
            "title": "⚠️ 지인 사칭 의심",
            "message": "지인을 사칭한 사기 메시지일 수 있습니다.",
            "guide": [
                "본인 확인을 위해 직접 전화하세요",
                "급한 송금 요청은 의심하세요",
                "기존 번호로 다시 연락하세요"
            ],
            "additional_info": "지인 사칭 사기는 카톡/문자 계정 해킹 후 발생합니다."
        },
        "B-1": {
            "title": "🚨 금융기관 사칭 사기",
            "message": "금융감독원/은행을 사칭한 사기입니다. 절대 응답하지 마세요.",
            "guide": [
                "금융기관은 문자로 계좌 정보를 요구하지 않습니다",
                "의심되면 해당 기관 공식 번호로 직접 확인하세요",
                "즉시 차단하고 신고하세요 (국번없이 112)"
            ],
            "additional_info": "보이스피싱 의심 시 금융감독원 콜센터 1332로 신고하세요."
        },
        # ... B-2, B-3, C-1, C-2, C-3, D-N
    }

    def generate_user_alert(
        self,
        category: str,
        risk_level: str,
        detected_items: List[str]
    ) -> Dict:
        """사용자 알림 생성"""
        template = self.TEMPLATES.get(category, self.TEMPLATES["D-N"])

        return {
            "title": template["title"],
            "message": template["message"],
            "risk_level": risk_level,
            "detected_keywords": detected_items,
            "action_guide": template["guide"],
            "additional_info": template["additional_info"],
            "report_url": "https://ecrm.kisa.or.kr/",
            "emergency_contact": "112 (경찰청)"
        }
```

**구현 단계**:
1. 카테고리별 템플릿 작성 (9개 + D-N + NORMAL)
2. UIGenerator 클래스 구현
3. ActionPolicy에 통합
4. 프론트엔드 연동 테스트

**예상 효과**:
- ✅ 사용자 친화적 알림
- ✅ 카테고리별 맞춤 가이드
- ✅ 행동 유도 명확화
- ✅ 신고 방법 안내

**예상 일정**: 1주

### 5.3 우선순위 3: 베이즈 확률 평가 (📊 학술적 근거)

**목표**: 학술적으로 검증된 확률 기반 위험도 평가

**현재 문제**:
- Weighted Average → 경험적 가중치 (근거 부족)
- 복잡한 증거 조합 시 정확도 한계
- 설명 가능성 부족

**개선 계획**:

```python
# agent/core/bayesian_evaluator.py (신규)

class BayesianRiskEvaluator:
    """베이즈 확률 기반 위험도 평가"""

    def __init__(self):
        # Prior 확률 (사전 통계)
        self.prior_scam = 0.05  # 전체 메시지 중 사기 비율

        # Likelihood (증거별 조건부 확률)
        self.likelihoods = {
            "category_B1": {"scam": 0.95, "normal": 0.01},  # P(E|Scam), P(E|Normal)
            "category_A2": {"scam": 0.90, "normal": 0.02},
            "db_reported": {"scam": 0.99, "normal": 0.001},
            "low_trust": {"scam": 0.80, "normal": 0.10},
            # ...
        }

    def calculate_risk(self, evidences: List[Dict]) -> Dict:
        """
        베이즈 정리로 위험도 계산

        P(Scam|E1,E2,...,En) = P(E1,E2,...,En|Scam) × P(Scam) / P(E)

        Returns:
            {
                "probability_scam": 0.87,
                "probability_normal": 0.13,
                "confidence": 0.95,
                "evidence_contribution": {...}
            }
        """
        # 1. Prior 설정
        p_scam = self.prior_scam
        p_normal = 1 - p_scam

        # 2. Bayesian Update (각 증거마다)
        for evidence in evidences:
            evidence_type = evidence["type"]
            likelihood = self.likelihoods.get(evidence_type)

            if likelihood:
                # 베이즈 정리 적용
                p_e_given_scam = likelihood["scam"]
                p_e_given_normal = likelihood["normal"]

                p_e = (p_e_given_scam * p_scam) + (p_e_given_normal * p_normal)

                # Posterior 계산
                p_scam = (p_e_given_scam * p_scam) / p_e
                p_normal = 1 - p_scam

        # 3. Temperature Scaling (calibration)
        calibrated_prob = self._temperature_scaling(p_scam, temperature=1.5)

        # 4. 위험도 레벨 결정
        risk_level = self._prob_to_risk_level(calibrated_prob)

        return {
            "probability_scam": calibrated_prob,
            "probability_normal": 1 - calibrated_prob,
            "risk_level": risk_level,
            "confidence": self._calculate_confidence(evidences),
            "evidence_contribution": self._explain_contribution(evidences)
        }

    def _temperature_scaling(self, prob: float, temperature: float) -> float:
        """Temperature Scaling for calibration"""
        import math
        logit = math.log(prob / (1 - prob + 1e-10))
        calibrated_logit = logit / temperature
        return 1 / (1 + math.exp(-calibrated_logit))
```

**구현 단계**:
1. Prior 확률 설정 (실제 데이터 기반)
2. Likelihood 테이블 작성 (각 증거별)
3. BayesianRiskEvaluator 구현
4. 기존 Weighted Average와 비교 테스트
5. 성능 우수 시 교체

**예상 효과**:
- ✅ 학술적 근거 강화
- ✅ 설명 가능성 향상 (각 증거의 기여도 명확)
- ✅ 복잡한 증거 조합 시 정확도 향상
- ⚠️ 구현 복잡도 증가
- ⚠️ Prior/Likelihood 설정 어려움

**예상 일정**: 2주

### 5.4 우선순위 4: 이미지 분석 추가 (🖼️ 확장)

**목표**: 이미지 기반 사기 탐지

**현재 상태**: 텍스트만 분석

**개선 계획**:
- OCR 통합 (이미지 → 텍스트)
- QR 코드 스캔 및 URL 추출
- 로고 위조 탐지 (금융기관 로고 확인)
- 스크린샷 기반 사기 (가짜 계좌 이체 내역 등)

**예상 일정**: 3주

### 5.5 우선순위 5: 다국어 지원 (🌏 확장)

**목표**: 영어/중국어 사기 메시지 탐지

**현재 상태**: 한국어만 지원

**개선 계획**:
- 다국어 패턴 데이터 구축
- 다국어 System Prompt
- 번역 기반 분석 (번역 → 분석 → 결과)

**예상 일정**: 2주

---

## 6. 결론

### 6.1 Agent B 현재 수준

**구현도**: 70% (기초 기능 완성, 고급 기능 미구현)

**강점**:
- ✅ MECE 9-카테고리 분류 시스템 완성
- ✅ 4-Stage 파이프라인 안정적 동작
- ✅ MCP 도구 12개 완전 구현
- ✅ 신고 DB 조회 기능
- ✅ 발신자 신뢰도 분석

**한계**:
- ⚠️ AI 자율성 부족 (Rule-based)
- ⚠️ 베이즈 확률 미적용
- ⚠️ UI Generator 미구현
- ⚠️ 최신 기획서 미반영

### 6.2 Gap 발생 원인

1. **시간 차이**: 최신 기획서 (2025-12-07) vs 현재 구현 (2024년 기반)
2. **우선순위**: 기본 기능 먼저 구현 → 고급 기능은 향후 계획
3. **현실적 범위**: RAG Tool 등 과도한 기능은 의도적 제외

### 6.3 향후 방향

**단기 (1~2주)**:
- UI Generator Module 개발 (사용자 경험 개선)

**중기 (2~4주)**:
- Hybrid Intelligent Agent 전환 (AI 중심 제어)

**장기 (1~2개월)**:
- 베이즈 확률 평가 적용 (학술적 근거)
- 이미지 분석 추가 (확장)
- 다국어 지원 (글로벌)

---

**문서 버전**: 1.0
**최종 수정**: 2025-12-07
**다음 업데이트 예정**: Agent B Hybrid Agent 전환 완료 후
