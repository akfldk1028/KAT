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

    Args:
        text: 분석할 텍스트

    Returns:
        {
            "found_pii": [{"id": "...", "category": "...", "value": "...", "risk_level": "..."}],
            "categories_found": ["personal_info", "financial_info"],
            "highest_risk": "MEDIUM"
        }
    """
    data = _get_patterns_data()
    found_pii = []
    categories_found = set()
    highest_risk = RiskLevel.LOW

    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

    for cat_id, cat_info in data["categories"].items():
        for item in cat_info["items"]:
            regex = item.get("regex")
            keywords = item.get("keywords", [])

            # 정규식 매칭
            if regex:
                try:
                    matches = re.findall(regex, text)
                    for match in matches:
                        found_pii.append({
                            "id": item["id"],
                            "category": cat_id,
                            "value": match if isinstance(match, str) else match[0],
                            "risk_level": item["risk_level"],
                            "name_ko": item["name_ko"]
                        })
                        categories_found.add(cat_id)
                        if risk_order[item["risk_level"]] > risk_order[highest_risk.value]:
                            highest_risk = RiskLevel(item["risk_level"])
                except re.error:
                    continue

            # 키워드 매칭 (requires_ai가 아닌 경우만)
            if not item.get("requires_ai", False):
                for keyword in keywords:
                    if keyword.lower() in text.lower():
                        # 키워드만 있으면 PII로 기록하지 않음 (컨텍스트 필요)
                        # 단, regex 매칭이 없고 키워드만 있으면 AI 분석 필요 표시
                        pass

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
