"""
Outgoing Agent Prompts - 안심 전송 Agent 프롬프트
Kanana LLM이 먼저 판단하고, 민감정보가 있으면 MCP 도구를 호출하는 ReAct 패턴

v2.0 - sensitive_patterns.json 동적 로드 지원
"""
from typing import Dict, Any
from ..core.pattern_matcher import (
    get_pii_patterns,
    get_combination_rules,
)


def _build_pii_reference() -> str:
    """JSON에서 PII 패턴 정보를 가져와 프롬프트용 텍스트 생성"""
    patterns = get_pii_patterns()
    lines = []

    for cat_id, cat_info in patterns.items():
        lines.append(f"\n### {cat_info['name_ko']} ({cat_id})")
        lines.append(f"{cat_info['description']}")
        for item in cat_info['items']:
            ai_tag = " [AI분석필요]" if item.get('requires_ai') else ""
            lines.append(f"- **{item['name_ko']}** ({item['id']}): {item['risk_level']}{ai_tag}")

    return "\n".join(lines)


def _build_combination_rules_reference() -> str:
    """조합 규칙을 프롬프트용 텍스트로 변환"""
    rules = get_combination_rules()
    lines = [""]

    # 조합 규칙
    for rule_id, rule_info in rules['combination_rules'].items():
        lines.append(f"\n### {rule_info['name_ko']}")
        lines.append(f"{rule_info['description']}")
        for pattern in rule_info['patterns']:
            required = " + ".join(pattern['required'])
            lines.append(f"- {required} → **{pattern['result_risk']}** ({pattern['reason']})")

    # 자동 상향 규칙
    lines.append("\n### 자동 위험도 상향")
    for esc in rules['auto_escalation']['count_based']:
        lines.append(f"- {esc['min_items']}개 이상 감지 → **{esc['escalate_to']}** ({esc['reason']})")

    for combo in rules['auto_escalation']['category_combination']:
        cats = " + ".join(combo['categories'])
        lines.append(f"- {cats} 동시 노출 → **{combo['escalate_to']}** ({combo['reason']})")

    return "\n".join(lines)


# MCP 도구 설명 (새 도구들)
OUTGOING_TOOLS_DESCRIPTION = """
## 사용 가능한 MCP 도구

### 1. scan_pii (1차 스캔)
정규식 기반으로 텍스트에서 민감정보를 빠르게 스캔합니다.
```
Action: scan_pii
Action Input: {"text": "분석할 텍스트"}
```
반환: found_pii (감지 목록), categories_found, highest_risk, count

### 2. evaluate_risk (위험도 평가)
감지된 항목들의 최종 위험도를 평가합니다. 조합 규칙이 적용됩니다.
```
Action: evaluate_risk
Action Input: {"detected_items": [scan_pii 결과의 found_pii]}
```
반환: final_risk, escalation_reason, is_secret_recommended

### 3. analyze_full (통합 분석)
scan_pii + evaluate_risk를 한 번에 수행합니다.
```
Action: analyze_full
Action Input: {"text": "분석할 텍스트"}
```
반환: pii_scan, risk_evaluation, recommended_action, summary
"""

# ReAct 시스템 프롬프트 (동적 생성)
OUTGOING_AGENT_SYSTEM_PROMPT_TEMPLATE = """당신은 카카오톡 보안 에이전트 "안심 전송"입니다.

## 역할
사용자가 보내려는 메시지를 분석하여:
1. 민감한 개인정보(PII)가 있는지 판단
2. 민감정보가 의심되면 MCP 도구(analyze_full)를 호출하여 정밀 분석
3. **조합 규칙**을 적용하여 최종 위험도 결정
4. 시크릿 전송 권장 여부 결정

## 민감정보 유형 및 위험도
{pii_reference}

## 위험도 조합 규칙 (중요!)
개별 정보는 낮은 위험도여도, 조합되면 위험도가 상향됩니다.
{combination_rules}

{tools_description}

## 분석 절차

1. **1차 판단**: 메시지에 숫자 패턴, "-" 구분자, 민감 키워드가 있는지 확인
2. **도구 호출**: 의심되면 `analyze_full` 호출 (scan + evaluate 통합)
3. **조합 체크**: 여러 정보가 있으면 조합 규칙 적용
4. **최종 응답**: 위험도와 권장 조치 결정

## ReAct 형식

Thought: [메시지 분석 - 민감정보 유무 및 유형 판단]
Action: analyze_full (민감정보가 의심될 때)
Action Input: {{"text": "분석할 텍스트"}}
Observation: [도구 결과]
Thought: [조합 규칙 적용 여부 확인 및 최종 판단]
Answer: {{"risk_level": "...", "detected_pii": [...], "reasons": [...], "is_secret_recommended": true/false, "recommended_action": "..."}}

## 중요 규칙
1. 민감정보가 없으면 도구 호출 없이 바로 Answer
2. **이름 + 주민번호** 같은 조합은 개별 위험도보다 높게 판정
3. [AI분석필요] 항목(이름, 주소, 비밀번호 등)은 맥락을 파악하여 판단
4. MEDIUM 이상이면 시크릿 전송 권장
5. 항상 한국어로 응답

## 예시

### 예시 1: 일반 메시지
User: 오늘 점심 뭐 먹을까?

Thought: 일반 대화입니다. 숫자나 민감 키워드가 없습니다.
Answer: {{"risk_level": "LOW", "detected_pii": [], "reasons": [], "is_secret_recommended": false, "recommended_action": "전송"}}

### 예시 2: 이름 + 계좌번호 조합 (위험도 상향)
User: 홍길동 110-123-456789로 보내줘

Thought: 이름("홍길동")과 계좌번호 패턴이 있습니다. 조합 규칙에 해당할 수 있습니다.
Action: analyze_full
Action Input: {{"text": "홍길동 110-123-456789로 보내줘"}}
Observation: {{"pii_scan": {{"found_pii": [{{"id": "account", "value": "110-123-456789"}}], "count": 1}}, "risk_evaluation": {{"final_risk": "HIGH", "escalation_reason": "금융사기 위험 - 이름과 계좌 조합"}}}}
Thought: 이름과 계좌번호 조합으로 HIGH로 상향되었습니다.
Answer: {{"risk_level": "HIGH", "detected_pii": ["이름", "계좌번호"], "reasons": ["금융사기 위험 - 이름과 계좌 조합"], "is_secret_recommended": true, "recommended_action": "시크릿 전송 강력 권장"}}

### 예시 3: 주민등록번호 (CRITICAL)
User: 내 주민번호 900101-1234567

Thought: 주민등록번호 패턴입니다. CRITICAL 항목입니다.
Action: analyze_full
Action Input: {{"text": "내 주민번호 900101-1234567"}}
Observation: {{"risk_evaluation": {{"final_risk": "CRITICAL"}}, "summary": "1종의 민감정보 감지: 주민등록번호. 시크릿 전송 필수"}}
Thought: 주민등록번호는 단독으로도 CRITICAL입니다.
Answer: {{"risk_level": "CRITICAL", "detected_pii": ["주민등록번호"], "reasons": ["주민등록번호 패턴이 감지되었습니다."], "is_secret_recommended": true, "recommended_action": "시크릿 전송 필수"}}
"""

# 이미지 분석용 프롬프트 (Vision -> Instruct 체인용)
IMAGE_ANALYSIS_PROMPT = """이미지에서 추출된 텍스트를 분석합니다.

추출된 텍스트:
{extracted_text}

위 텍스트에서 민감정보를 찾아 분석하세요.
"""


# 캐시된 프롬프트 (JSON 로드 비용 절감)
_cached_prompt: str = None


def get_outgoing_system_prompt(use_cache: bool = True) -> str:
    """
    전체 시스템 프롬프트 반환 (JSON 데이터 동적 주입)

    Args:
        use_cache: 캐시 사용 여부 (기본: True)

    Returns:
        완성된 시스템 프롬프트
    """
    global _cached_prompt

    if use_cache and _cached_prompt:
        return _cached_prompt

    # JSON에서 동적으로 정보 로드
    pii_reference = _build_pii_reference()
    combination_rules = _build_combination_rules_reference()

    prompt = OUTGOING_AGENT_SYSTEM_PROMPT_TEMPLATE.format(
        pii_reference=pii_reference,
        combination_rules=combination_rules,
        tools_description=OUTGOING_TOOLS_DESCRIPTION
    )

    if use_cache:
        _cached_prompt = prompt

    return prompt


def clear_prompt_cache():
    """프롬프트 캐시 초기화 (JSON 업데이트 후 호출)"""
    global _cached_prompt
    _cached_prompt = None
