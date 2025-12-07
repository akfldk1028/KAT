"""
Pattern Matcher - sensitive_patterns.json 기반 패턴 매칭
AI가 MCP 도구를 통해 호출하는 핵심 분석 모듈
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from functools import lru_cache
from ..core.models import RiskLevel


# JSON 데이터 캐시
_patterns_cache: Optional[Dict] = None


def _get_patterns_data() -> Dict:
    """sensitive_patterns.json 로드 (캐시 사용)"""
    global _patterns_cache
    if _patterns_cache is None:
        json_path = Path(__file__).parent.parent / "data" / "sensitive_patterns.json"
        with open(json_path, "r", encoding="utf-8") as f:
            _patterns_cache = json.load(f)
    return _patterns_cache


def get_pii_patterns() -> Dict[str, List[Dict]]:
    """
    MCP Tool: 모든 PII 패턴 정보 반환
    AI가 어떤 종류의 민감정보가 있는지 파악하는 데 사용

    Returns:
        카테고리별 패턴 목록
    """
    data = _get_patterns_data()
    result = {}

    for cat_id, cat_info in data["categories"].items():
        result[cat_id] = {
            "name_ko": cat_info["name_ko"],
            "description": cat_info["description"],
            "items": [
                {
                    "id": item["id"],
                    "name_ko": item["name_ko"],
                    "risk_level": item["risk_level"],
                    "requires_ai": item.get("requires_ai", False)
                }
                for item in cat_info["items"]
            ]
        }

    return result


def get_document_types() -> List[Dict]:
    """
    MCP Tool: 문서 유형 목록 반환
    Vision OCR로 추출한 텍스트에서 서류 종류를 식별하는 데 사용

    Returns:
        문서 유형 목록 (이미지 감지용)
    """
    data = _get_patterns_data()
    return [
        {
            "id": item["id"],
            "name_ko": item["name_ko"],
            "risk_level": item["risk_level"],
            "keywords": item["keywords"]
        }
        for item in data["document_types"]["items"]
    ]


# === [수정] 의미 기반 정규화 함수 추가 ===
# 프롬프트에서 약속한 "공일공-일이삼사-오육칠팔" → "010-1234-5678" 변환 기능 구현
# 제1원칙 (유일성 차단)의 Semantic Normalization 기술 구현
def normalize_korean_numbers(text: str) -> str:
    """
    한글 숫자를 아라비아 숫자로 정규화

    변칙 표기를 표준 포맷으로 변환하여 탐지율 향상
    예: "공일공-일이삼사-오육칠팔" → "010-1234-5678"

    Args:
        text: 원본 텍스트

    Returns:
        정규화된 텍스트
    """
    korean_num_map = {
        '공': '0', '일': '1', '이': '2', '삼': '3', '사': '4',
        '오': '5', '육': '6', '칠': '7', '팔': '8', '구': '9',
        '영': '0'  # "영" 도 "0"으로 매핑
    }

    result = text
    for korean, arabic in korean_num_map.items():
        result = result.replace(korean, arabic)

    return result
# === [수정 끝] ===


def get_combination_rules() -> Dict[str, Any]:
    """
    MCP Tool: 조합 규칙 반환
    여러 민감정보가 함께 있을 때 위험도 상향 규칙

    Returns:
        combination_rules와 auto_escalation 정보
    """
    data = _get_patterns_data()
    return {
        "combination_rules": data["combination_rules"],
        "auto_escalation": data["auto_escalation"]
    }


def detect_pii(text: str) -> Dict[str, Any]:
    """
    MCP Tool: 텍스트에서 PII 감지
    정규식 기반으로 민감정보를 탐지하고 결과 반환

    중요: 우선순위가 높은 패턴(카드번호, 주민번호)을 먼저 매칭하고,
    이미 매칭된 부분은 다른 패턴으로 중복 감지하지 않음

    Args:
        text: 분석할 텍스트

    Returns:
        {
            "found_pii": [{"id": "...", "category": "...", "value": "...", "risk_level": "..."}],
            "categories_found": ["personal_info", "financial_info"],
            "highest_risk": "MEDIUM"
        }
    """
    # === [수정] 의미 기반 정규화 적용 ===
    # "공일공-일이삼사-오육칠팔" → "010-1234-5678" 변환하여 탐지율 향상
    normalized_text = normalize_korean_numbers(text)
    # === [수정 끝] ===

    data = _get_patterns_data()
    found_pii = []
    categories_found = set()
    highest_risk = RiskLevel.LOW

    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

    # 패턴 우선순위 정의 (높은 것 먼저 매칭)
    # 숫자가 낮을수록 먼저 매칭됨
    priority_order = {
        "resident_id": 1,      # 주민번호
        "foreigner_id": 1,     # 외국인등록번호
        "card": 2,             # 신용카드
        "passport": 3,         # 여권
        "driver_license": 3,   # 운전면허
        "phone": 4,            # 전화번호 (계좌번호보다 먼저 - 010 패턴 구분)
        "account": 5,          # 계좌번호
        "birth_date": 10,      # 생년월일 (가장 낮은 우선순위)
    }

    # 모든 패턴 수집
    all_patterns = []
    for cat_id, cat_info in data["categories"].items():
        for item in cat_info["items"]:
            if item.get("regex"):
                priority = priority_order.get(item["id"], 10)
                all_patterns.append({
                    "item": item,
                    "category": cat_id,
                    "priority": priority
                })

    # 우선순위순 정렬
    all_patterns.sort(key=lambda x: x["priority"])

    # 이미 매칭된 위치 추적 (중복 방지)
    matched_ranges = []

    def is_overlapping(start: int, end: int) -> bool:
        """이미 매칭된 범위와 겹치는지 확인"""
        for m_start, m_end in matched_ranges:
            # 겹치는 경우: 새 범위가 기존 범위 안에 포함되거나 교차
            if not (end <= m_start or start >= m_end):
                return True
        return False

    # 우선순위순 매칭
    for pattern_info in all_patterns:
        item = pattern_info["item"]
        cat_id = pattern_info["category"]
        regex = item["regex"]

        try:
            # === [수정] 정규화된 텍스트로 패턴 매칭 ===
            for match in re.finditer(regex, normalized_text):
                start, end = match.start(), match.end()
                matched_value = match.group()  # 정규화된 값 사용
                # === [수정 끝] ===

                # 이미 매칭된 범위와 겹치면 스킵
                if is_overlapping(start, end):
                    continue

                # 새 매칭 추가
                matched_ranges.append((start, end))
                found_pii.append({
                    "id": item["id"],
                    "category": cat_id,
                    "value": matched_value,
                    "risk_level": item["risk_level"],
                    "name_ko": item["name_ko"]
                })
                categories_found.add(cat_id)
                if risk_order[item["risk_level"]] > risk_order[highest_risk.value]:
                    highest_risk = RiskLevel(item["risk_level"])
        except re.error:
            continue

    return {
        "found_pii": found_pii,
        "categories_found": list(categories_found),
        "highest_risk": highest_risk.value,
        "count": len(found_pii)
    }


def detect_document_type(text: str) -> Dict[str, Any]:
    """
    MCP Tool: OCR 텍스트에서 문서 유형 감지

    Args:
        text: OCR로 추출한 텍스트

    Returns:
        {
            "document_type": "resident_card",
            "name_ko": "주민등록증",
            "risk_level": "CRITICAL",
            "confidence": "high/medium/low"
        }
    """
    data = _get_patterns_data()
    text_lower = text.lower()

    best_match = None
    best_score = 0

    for item in data["document_types"]["items"]:
        score = 0
        for keyword in item["keywords"]:
            if keyword.lower() in text_lower:
                score += 1

        if score > best_score:
            best_score = score
            best_match = item

    if best_match and best_score > 0:
        confidence = "high" if best_score >= 2 else "medium" if best_score == 1 else "low"
        return {
            "document_type": best_match["id"],
            "name_ko": best_match["name_ko"],
            "risk_level": best_match["risk_level"],
            "confidence": confidence,
            "matched_keywords": best_score
        }

    return {
        "document_type": None,
        "name_ko": None,
        "risk_level": "LOW",
        "confidence": "none"
    }


def calculate_risk(detected_items: List[Dict]) -> Dict[str, Any]:
    """
    MCP Tool: 감지된 항목들의 최종 위험도 계산
    조합 규칙과 자동 상향 규칙 적용

    Args:
        detected_items: detect_pii()에서 반환된 found_pii 목록

    Returns:
        {
            "final_risk": "CRITICAL",
            "base_risk": "MEDIUM",
            "escalation_reason": "신원도용 위험 - 이름과 주민번호 조합",
            "is_secret_recommended": true,
            "matched_rules": ["identity_theft"]
        }
    """
    if not detected_items:
        return {
            "final_risk": "LOW",
            "base_risk": "LOW",
            "escalation_reason": None,
            "is_secret_recommended": False,
            "matched_rules": []
        }

    data = _get_patterns_data()
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

    # 1. 기본 위험도 (가장 높은 개별 항목)
    base_risk = "LOW"
    for item in detected_items:
        if risk_order[item["risk_level"]] > risk_order[base_risk]:
            base_risk = item["risk_level"]

    final_risk = base_risk
    escalation_reason = None
    matched_rules = []

    # 감지된 항목 ID 집합
    detected_ids = {item["id"] for item in detected_items}
    detected_categories = {item["category"] for item in detected_items}

    # 2. 조합 규칙 체크
    for rule_id, rule_info in data["combination_rules"].items():
        for pattern in rule_info["patterns"]:
            required = set(pattern["required"])
            any_of = set(pattern.get("any_of", []))

            # required 모두 충족
            if required.issubset(detected_ids):
                # any_of가 있으면 하나 이상 충족 필요
                if not any_of or any_of.intersection(detected_ids):
                    result_risk = pattern["result_risk"]
                    if risk_order[result_risk] > risk_order[final_risk]:
                        final_risk = result_risk
                        escalation_reason = f"{rule_info['name_ko']} - {pattern['reason']}"
                        matched_rules.append(rule_id)

    # 3. 자동 상향 규칙 (count_based)
    count = len(detected_items)
    for escalation in data["auto_escalation"]["count_based"]:
        if count >= escalation["min_items"]:
            if risk_order[escalation["escalate_to"]] > risk_order[final_risk]:
                final_risk = escalation["escalate_to"]
                escalation_reason = escalation["reason"]

    # 4. 카테고리 조합 상향
    for combo in data["auto_escalation"]["category_combination"]:
        required_cats = set(combo["categories"])
        if required_cats.issubset(detected_categories):
            if risk_order[combo["escalate_to"]] > risk_order[final_risk]:
                final_risk = combo["escalate_to"]
                escalation_reason = combo["reason"]

    # 시크릿 전송 권장 여부
    is_secret_recommended = risk_order[final_risk] >= risk_order["MEDIUM"]

    return {
        "final_risk": final_risk,
        "base_risk": base_risk,
        "escalation_reason": escalation_reason,
        "is_secret_recommended": is_secret_recommended,
        "matched_rules": matched_rules,
        "detected_count": count
    }


def get_risk_action(risk_level: str) -> str:
    """위험도에 따른 권장 조치 반환"""
    data = _get_patterns_data()
    risk_info = data["risk_levels"].get(risk_level, {})
    return risk_info.get("action", "전송")
