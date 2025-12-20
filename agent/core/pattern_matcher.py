"""
Pattern Matcher - sensitive_patterns.json 기반 패턴 매칭
AI가 MCP 도구를 통해 호출하는 핵심 분석 모듈
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
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


# === [추가] 은행 키워드 목록 (컨텍스트 기반 계좌 탐지용) ===
BANK_KEYWORDS = [
    # 인터넷/시중은행
    "카카오뱅크", "카카오", "토스뱅크", "토스", "케이뱅크", "케이bank",
    "KB국민", "국민은행", "국민", "신한은행", "신한", "우리은행", "우리",
    "하나은행", "하나", "IBK기업", "기업은행", "기업", "SC제일", "씨티",
    # 특수/상호금융
    "NH농협", "농협은행", "농협", "단위농협", "우체국", "새마을금고", "신협", "수협", "산림조합",
    # 지방은행
    "대구은행", "DGB", "부산은행", "BNK", "경남은행", "광주은행", "전북은행", "제주은행",
    # 증권사
    "키움증권", "키움", "미래에셋", "한국투자", "삼성증권", "NH투자", "KB증권",
    "신한투자", "하나증권", "대신증권", "메리츠", "유안타", "한화투자", "유진투자",
    "DB금융", "교보증권", "하이투자", "현대차증권", "신영증권", "이베스트", "SK증권",
    "토스증권", "카카오페이증권",
    # 일반 키워드
    "은행", "계좌", "통장", "입금", "송금", "이체", "예금주"
]


def _has_bank_context(text: str, match_start: int, window: int = 20) -> bool:
    """
    매칭된 숫자 주변에 은행 키워드가 있는지 확인

    Args:
        text: 전체 텍스트
        match_start: 매칭 시작 위치
        window: 앞뒤로 확인할 문자 수

    Returns:
        은행 키워드 존재 여부
    """
    # 매칭 위치 앞뒤 window 문자 추출
    context_start = max(0, match_start - window)
    context_end = min(len(text), match_start + window)
    context = text[context_start:context_end].lower()

    for keyword in BANK_KEYWORDS:
        if keyword.lower() in context:
            return True
    return False


def detect_context_accounts(text: str, existing_matches: List[Tuple[int, int]]) -> List[Dict]:
    """
    컨텍스트 기반 계좌번호 탐지
    은행 키워드가 주변에 있으면 10-14자리 숫자를 계좌번호로 판단

    - 평생계좌: 010-xxxx-xxxx + 은행명 → 계좌번호
    - 일반 계좌: 10-14자리 연속 숫자 + 은행명 → 계좌번호

    Args:
        text: 분석할 텍스트
        existing_matches: 이미 매칭된 범위 목록 (중복 방지)

    Returns:
        감지된 계좌번호 목록
    """
    accounts = []

    # 패턴 1: 평생계좌 (010으로 시작, 하이픈 포함/미포함)
    lifetime_pattern = r'010[\s\-]?\d{4}[\s\-]?\d{4}'

    # 패턴 2: 일반 10-14자리 연속 숫자 (기존 정규식에서 못 잡는 경우)
    general_pattern = r'\d{10,14}'

    def is_overlapping(start: int, end: int) -> bool:
        for m_start, m_end in existing_matches:
            if not (end <= m_start or start >= m_end):
                return True
        return False

    # 평생계좌 탐지 (은행 컨텍스트 필수)
    for match in re.finditer(lifetime_pattern, text):
        start, end = match.start(), match.end()
        if is_overlapping(start, end):
            continue

        # 은행 키워드가 주변에 있으면 계좌번호로 판단
        if _has_bank_context(text, start, window=15):
            accounts.append({
                "id": "account",
                "category": "financial_info",
                "value": match.group(),
                "risk_level": "CRITICAL",
                "name_ko": "계좌번호(평생계좌)",
                "context_based": True
            })
            existing_matches.append((start, end))

    # 일반 연속 숫자 탐지 (은행 컨텍스트 필수)
    for match in re.finditer(general_pattern, text):
        start, end = match.start(), match.end()
        if is_overlapping(start, end):
            continue

        value = match.group()
        digit_count = len(value)

        # 10-14자리만 허용 (카드번호 16자리 제외, 날짜 8자리 제외)
        if digit_count < 10 or digit_count > 14:
            continue

        # 은행 키워드가 주변에 있으면 계좌번호로 판단
        if _has_bank_context(text, start, window=15):
            accounts.append({
                "id": "account",
                "category": "financial_info",
                "value": value,
                "risk_level": "CRITICAL",
                "name_ko": "계좌번호",
                "context_based": True
            })
            existing_matches.append((start, end))

    return accounts


# === [수정] 의미 기반 정규화 함수 추가 ===
# 프롬프트에서 약속한 "공일공-일이삼사-오육칠팔" → "010-1234-5678" 변환 기능 구현
# 제1원칙 (유일성 차단)의 Semantic Normalization 기술 구현
def normalize_korean_numbers(text: str) -> str:
    """
    한글 숫자를 아라비아 숫자로 정규화

    변칙 표기를 표준 포맷으로 변환하여 탐지율 향상
    예: "공일공-일이삼사-오육칠팔" → "010-1234-5678"
    예: "구공공일일오 다시 일이삼사오육칠" → "900115-1234567"

    Args:
        text: 원본 텍스트

    Returns:
        정규화된 텍스트
    """
    import re

    korean_num_map = {
        '공': '0', '일': '1', '이': '2', '삼': '3', '사': '4',
        '오': '5', '육': '6', '칠': '7', '팔': '8', '구': '9',
        '영': '0'  # "영" 도 "0"으로 매핑
    }

    result = text
    for korean, arabic in korean_num_map.items():
        result = result.replace(korean, arabic)

    # === [추가] 구분자 정규화 ===
    # "다시", "에", 띄어쓰기 등 숫자 사이 구분자를 하이픈으로 변환
    # 예: "900115 다시 1234567" → "900115-1234567"
    separator_patterns = [
        (r'(\d+)\s*다시\s*(\d+)', r'\1-\2'),  # "다시" → 하이픈
        (r'(\d+)\s*에\s*(\d+)', r'\1-\2'),    # "에" → 하이픈 (공일공에 일이삼사)
        (r'(\d{6})\s+([1-4]\d{6})', r'\1-\2'),  # 주민번호: 6자리 + 공백 + 7자리(1-4로 시작)
        (r'(\d{3})\s+(\d{4})\s+(\d{4})', r'\1-\2-\3'),  # 전화번호: 3-4-4
        (r'(\d{4})\s+(\d{4})\s+(\d{4})\s+(\d{4})', r'\1-\2-\3-\4'),  # 카드번호: 4-4-4-4
    ]

    for pattern, replacement in separator_patterns:
        result = re.sub(pattern, replacement, result)
    # === [추가 끝] ===

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
        "account_prefix": 3,   # 계좌번호(은행접두사) - 전화번호보다 높은 우선순위!
        "passport": 4,         # 여권
        "driver_license": 4,   # 운전면허
        "phone": 5,            # 전화번호
        "account": 6,          # 계좌번호 (하이픈 형식)
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

    # === [추가] 평생계좌 재분류 (전화번호 → 계좌번호) ===
    # 은행 키워드와 함께 있는 010 전화번호는 평생계좌로 재분류
    phone_items_to_reclassify = []
    for i, item in enumerate(found_pii):
        if item["id"] == "phone" and item["value"].startswith("010"):
            # 전화번호 위치 찾기
            phone_start = normalized_text.find(item["value"])
            if phone_start >= 0 and _has_bank_context(normalized_text, phone_start, window=15):
                phone_items_to_reclassify.append(i)

    # 역순으로 재분류 (인덱스 유지)
    for i in reversed(phone_items_to_reclassify):
        old_item = found_pii[i]
        found_pii[i] = {
            "id": "account",
            "category": "financial_info",
            "value": old_item["value"],
            "risk_level": "CRITICAL",
            "name_ko": "계좌번호(평생계좌)",
            "context_based": True
        }
        categories_found.add("financial_info")
        if risk_order["CRITICAL"] > risk_order[highest_risk.value]:
            highest_risk = RiskLevel.CRITICAL
    # === [추가 끝] ===

    # === [추가] 컨텍스트 기반 계좌번호 탐지 ===
    # 기존 정규식에서 못 잡는 계좌번호를 은행 키워드 컨텍스트로 추가 탐지
    # 예: "신한 110277121051" (하이픈 없는 12자리)
    context_accounts = detect_context_accounts(normalized_text, matched_ranges)
    for acc in context_accounts:
        found_pii.append(acc)
        categories_found.add(acc["category"])
        if risk_order[acc["risk_level"]] > risk_order[highest_risk.value]:
            highest_risk = RiskLevel(acc["risk_level"])
    # === [추가 끝] ===

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
    import re
    data = _get_patterns_data()
    text_lower = text.lower()
    # OCR 공백 제거 버전 (띄어쓰기로 인한 키워드 누락 방지)
    text_no_space = re.sub(r'\s+', '', text_lower)

    best_match = None
    best_score = 0

    # 주민등록증 특수 감지 - OCR에서 자주 나오는 변형 패턴
    resident_card_patterns = [
        '주민등록증', '주민 등록증', '주민등록 증',
        '신분증', 'resident', 'id card',
        '주민등록번호', '등록번호'
    ]

    for item in data["document_types"]["items"]:
        score = 0

        # 1. 일반 키워드 매칭 (원본 텍스트)
        for keyword in item["keywords"]:
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower:
                score += 2  # 정확한 매칭은 가중치 2

        # 2. 공백 제거 후 매칭 (OCR 공백 문제 해결)
        for keyword in item["keywords"]:
            keyword_no_space = re.sub(r'\s+', '', keyword.lower())
            if keyword_no_space in text_no_space and keyword.lower() not in text_lower:
                score += 1  # 공백 제거 매칭은 가중치 1

        # 3. 주민등록증 특수 처리
        if item["id"] == "resident_card":
            for pattern in resident_card_patterns:
                pattern_no_space = re.sub(r'\s+', '', pattern.lower())
                if pattern_no_space in text_no_space:
                    score += 1

        if score > best_score:
            best_score = score
            best_match = item

    if best_match and best_score > 0:
        confidence = "high" if best_score >= 3 else "medium" if best_score >= 1 else "low"
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
    # [수정] 같은 ID는 1개로만 카운트 (이름이 여러 개 감지되어도 1개로 취급)
    count = len(detected_ids)
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
