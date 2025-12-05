"""
Threat Matcher - MECE 기반 피싱/사기 패턴 매칭 (v2.0)
AI(Agent B)가 MCP 도구를 통해 호출하는 수신 메시지 분석 모듈

카테고리 분류:
- A: 관계 사칭형 (Targeting Trust)
- B: 공포/권위 악용형 (Targeting Fear & Authority)
- C: 욕망/감정 자극형 (Targeting Desire & Emotion)
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

# KISA 피싱사이트 API 통합 (선택 - API Key 있을 때만 활성화)
try:
    from .kisa_phishing_api import check_url_kisa
    KISA_AVAILABLE = True
except ImportError:
    KISA_AVAILABLE = False


# JSON 데이터 캐시
_threat_cache: Optional[Dict] = None


def _get_threat_data() -> Dict:
    """threat_patterns.json 로드 (캐시 사용)"""
    global _threat_cache
    if _threat_cache is None:
        json_path = Path(__file__).parent.parent / "data" / "threat_patterns.json"
        with open(json_path, "r", encoding="utf-8") as f:
            _threat_cache = json.load(f)
    return _threat_cache


def reload_threat_data() -> None:
    """캐시 초기화 (패턴 파일 수정 시 호출)"""
    global _threat_cache
    _threat_cache = None


def get_all_categories() -> Dict[str, Any]:
    """
    MCP Tool: 모든 카테고리 정보 반환
    AI가 어떤 종류의 위협 카테고리가 있는지 파악하는 데 사용

    Returns:
        카테고리별 정보 (A, B, C)
    """
    data = _get_threat_data()
    result = {}

    for cat_id, cat_info in data["categories"].items():
        result[cat_id] = {
            "name_ko": cat_info["name_ko"],
            "name_en": cat_info["name_en"],
            "description": cat_info["description"],
            "psychological_trigger": cat_info["psychological_trigger"],
            "main_channel": cat_info["main_channel"],
            "patterns": list(cat_info["patterns"].keys())
        }

    return result


def get_pattern_details(pattern_id: str) -> Optional[Dict]:
    """
    MCP Tool: 특정 패턴의 상세 정보 반환

    Args:
        pattern_id: 패턴 ID (예: "A-1", "B-2")

    Returns:
        패턴 상세 정보
    """
    data = _get_threat_data()
    cat_id = pattern_id.split("-")[0]

    if cat_id in data["categories"]:
        patterns = data["categories"][cat_id]["patterns"]
        if pattern_id in patterns:
            return patterns[pattern_id]

    return None


def detect_threats(text: str) -> Dict[str, Any]:
    """
    MCP Tool: 텍스트에서 위협 패턴 감지 (MECE 카테고리 기반)

    Args:
        text: 분석할 수신 메시지

    Returns:
        {
            "matched_patterns": [{"id": "A-1", "category": "A", ...}],
            "primary_category": "A",
            "primary_pattern": "A-1",
            "scam_probability": 85,
            "matched_keywords": ["엄마", "폰 고장"]
        }
    """
    data = _get_threat_data()
    matched_patterns = []
    all_matched_keywords = []

    # 각 카테고리의 패턴 검사
    for cat_id, cat_info in data["categories"].items():
        for pattern_id, pattern in cat_info["patterns"].items():
            match_result = _check_pattern_match(text, pattern)

            if match_result["matched"]:
                matched_patterns.append({
                    "id": pattern_id,
                    "category": cat_id,
                    "category_name_ko": cat_info["name_ko"],
                    "pattern_name_ko": pattern["name_ko"],
                    "risk_score": pattern["risk_score"],
                    "matched_keywords": match_result["keywords"],
                    "match_strength": match_result["strength"]
                })
                all_matched_keywords.extend(match_result["keywords"])

    # 매칭 결과가 없으면
    if not matched_patterns:
        return {
            "matched_patterns": [],
            "primary_category": None,
            "primary_pattern": None,
            "scam_probability": 0,
            "matched_keywords": [],
            "risk_level": "safe"
        }

    # 가장 강력한 매칭 찾기 (risk_score * match_strength)
    matched_patterns.sort(
        key=lambda x: x["risk_score"] * x["match_strength"],
        reverse=True
    )
    primary = matched_patterns[0]

    # 사기 확률 계산
    scam_probability = _calculate_scam_probability(text, matched_patterns, data)

    # 위험 레벨 결정
    risk_level = _get_risk_level(scam_probability, data)

    return {
        "matched_patterns": matched_patterns,
        "primary_category": primary["category"],
        "primary_pattern": primary["id"],
        "primary_pattern_name": primary["pattern_name_ko"],
        "scam_probability": scam_probability,
        "matched_keywords": list(set(all_matched_keywords)),
        "risk_level": risk_level
    }


def _check_pattern_match(text: str, pattern: Dict) -> Dict[str, Any]:
    """패턴 매칭 체크"""
    matched_keywords = []
    strength = 0.0

    # 키워드 체크
    keywords = pattern.get("keywords", [])
    found_keywords = [k for k in keywords if k in text]

    if not found_keywords:
        return {"matched": False, "keywords": [], "strength": 0}

    matched_keywords.extend(found_keywords)
    # 키워드 1개 이상 매칭되면 기본 0.3 + 추가 매칭에 따른 보너스
    keyword_base = 0.3 if found_keywords else 0
    keyword_bonus = min(len(found_keywords) / len(keywords), 0.5) * 0.4
    strength += keyword_base + keyword_bonus

    # 컨텍스트 키워드 체크
    context_keywords = pattern.get("context_keywords", [])
    if context_keywords:
        found_context = [k for k in context_keywords if k in text]
        if found_context:
            matched_keywords.extend(found_context)
            # 컨텍스트 2개 이상이면 강한 매칭
            context_score = min(len(found_context) / 3, 1.0) * 0.5
            strength += context_score
        else:
            # 컨텍스트 없이 키워드만 있으면 약한 매칭
            strength *= 0.5

    # URL 인디케이터 체크 (B 카테고리)
    url_indicators = pattern.get("url_indicators", [])
    if url_indicators:
        for indicator in url_indicators:
            if indicator.lower() in text.lower():
                matched_keywords.append(f"[URL:{indicator}]")
                strength += 0.2
                break

    # 전화번호 인디케이터 체크 (B-3)
    phone_indicators = pattern.get("phone_indicators", [])
    if phone_indicators:
        for indicator in phone_indicators:
            if indicator in text:
                matched_keywords.append(f"[Phone:{indicator}]")
                strength += 0.15
                break

    # 최소 강도 이상이면 매칭 (키워드 + 컨텍스트 2개 이상이면 매칭)
    has_keyword = len(found_keywords) >= 1
    has_context = len([k for k in context_keywords if k in text]) >= 2 if context_keywords else True
    matched = has_keyword and has_context and strength >= 0.3

    return {
        "matched": matched,
        "keywords": matched_keywords,
        "strength": min(strength, 1.0)
    }


def _calculate_scam_probability(
    text: str,
    matched_patterns: List[Dict],
    data: Dict
) -> int:
    """사기 확률(%) 계산"""
    if not matched_patterns:
        return 0

    # 기본 점수: 가장 높은 risk_score
    base_score = max(p["risk_score"] for p in matched_patterns)

    # 매칭 강도 반영
    primary_strength = matched_patterns[0]["match_strength"]
    score = base_score * primary_strength

    # 멀티플라이어 적용
    multipliers = data["scoring"]["multipliers"]

    # 여러 패턴 매칭
    if len(matched_patterns) > 1:
        score *= multipliers["multiple_patterns"]

    # URL 포함
    if re.search(r'https?://|bit\.ly|tinyurl|url\.kr|han\.gl', text, re.IGNORECASE):
        score *= multipliers["url_present"]

    # 전화번호 포함
    if re.search(r'02-\d{3,4}-\d{4}|0\d{2}-\d{3,4}-\d{4}|1[56]\d{2}-\d{4}|070-\d{4}-\d{4}', text):
        score *= multipliers["phone_number_present"]

    # 금액 포함
    if re.search(r'\d{2,3}만\s?원|\d{1,3},?\d{3},?\d{3}원|\$\d+|USD|JPY', text):
        score *= multipliers["money_amount_present"]

    # 긴급성 언어
    urgency_keywords = data["scoring"]["urgency_keywords"]
    if any(uk in text for uk in urgency_keywords):
        score *= multipliers["urgency_language"]

    # 안전 컨텍스트 체크 (false positive 방지)
    for safe_ctx in data["safe_patterns"]["safe_contexts"]:
        if any(k in text for k in safe_ctx["keywords"]):
            score *= safe_ctx["factor"]

    # 0-100 범위로 제한
    return min(int(score), 100)


def _get_risk_level(probability: int, data: Dict) -> str:
    """확률에 따른 위험 레벨 반환"""
    thresholds = data["scoring"]["base_threshold"]

    if probability <= thresholds["safe"]["max"]:
        return "safe"
    elif probability <= thresholds["low"]["max"]:
        return "low"
    elif probability <= thresholds["medium"]["max"]:
        return "medium"
    elif probability <= thresholds["high"]["max"]:
        return "high"
    else:
        return "critical"


def detect_urls(text: str) -> Dict[str, Any]:
    """
    MCP Tool: 텍스트에서 URL 감지 및 안전성 분석
    (Pattern-based + KISA 피싱사이트 DB 조회)

    Args:
        text: 분석할 텍스트

    Returns:
        URL 분석 결과
        - urls_found: 발견된 모든 URL
        - suspicious_urls: 의심스러운 URL (whitelist 제외)
        - safe_urls: 안전한 URL (whitelist 포함)
        - has_suspicious_url: Boolean
        - has_shortened_url: Boolean
        - kisa_phishing_urls: KISA DB에서 발견된 피싱 URL (신규)
        - phishing_count: 피싱 URL 개수 (신규)
    """
    data = _get_threat_data()

    # [1] Pattern-based 분석 (기존 로직)
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls_found = re.findall(url_pattern, text)

    # 단축 URL 패턴도 추가
    short_url_pattern = r'(?:bit\.ly|tinyurl\.com|goo\.gl|t\.co|is\.gd|v\.gd|me2\.do|vo\.la|url\.kr|han\.gl)/[\w]+'
    short_urls = re.findall(short_url_pattern, text, re.IGNORECASE)
    urls_found.extend([f"https://{u}" for u in short_urls])

    safe_domains = data.get("safe_patterns", {}).get("whitelist_domains", [])

    suspicious_urls = []
    safe_urls = []

    for url in urls_found:
        is_safe = any(safe_domain in url for safe_domain in safe_domains)
        if is_safe:
            safe_urls.append(url)
        else:
            suspicious_urls.append(url)

    # [2] KISA API 조회 (API Key 있을 때만)
    kisa_phishing_urls = []
    if KISA_AVAILABLE and suspicious_urls:
        for url in suspicious_urls:
            kisa_result = check_url_kisa(url)
            if kisa_result and kisa_result.get("is_phishing"):
                kisa_phishing_urls.append({
                    "url": url,
                    "matched_url": kisa_result["matched_url"],
                    "reported_date": kisa_result["reported_date"],
                    "source": "KISA"
                })

    return {
        "urls_found": urls_found,
        "suspicious_urls": suspicious_urls,
        "safe_urls": safe_urls,
        "has_suspicious_url": bool(suspicious_urls) or bool(kisa_phishing_urls),
        "has_shortened_url": bool(short_urls),
        "kisa_phishing_urls": kisa_phishing_urls,
        "phishing_count": len(kisa_phishing_urls)
    }


def analyze_incoming_message(text: str) -> Dict[str, Any]:
    """
    MCP Tool: 수신 메시지 종합 분석 (원스톱)
    모든 분석을 한 번에 수행

    Args:
        text: 분석할 수신 메시지

    Returns:
        종합 분석 결과 (scam_probability % 포함)
    """
    # 1. 위협 패턴 감지
    threats = detect_threats(text)

    # 2. URL 분석
    urls = detect_urls(text)

    # URL이 있으면 확률 조정
    if urls["has_suspicious_url"] and threats["scam_probability"] > 0:
        threats["scam_probability"] = min(
            int(threats["scam_probability"] * 1.1),
            100
        )

    # KISA 피싱 URL 발견 시 확률 추가 조정 (15% 부스트)
    if urls.get("phishing_count", 0) > 0:
        threats["scam_probability"] = min(
            int(threats["scam_probability"] * 1.15),
            100
        )

    # 3. 응답 템플릿 가져오기
    data = _get_threat_data()
    risk_level = threats["risk_level"]
    response_template = data["response_templates"].get(risk_level, data["response_templates"]["safe"])

    return {
        "text": text[:100] + "..." if len(text) > 100 else text,
        "threat_detection": threats,
        "url_analysis": urls,
        "final_assessment": {
            "scam_probability": threats["scam_probability"],
            "risk_level": risk_level,
            "matched_category": threats["primary_category"],
            "matched_pattern": threats["primary_pattern"],
            "pattern_name": threats.get("primary_pattern_name", ""),
            "warning_message": response_template["message"],
            "recommended_action": response_template["action"],
            "display_color": response_template["color"]
        },
        "summary": {
            "probability": f"{threats['scam_probability']}%",
            "category": threats["primary_pattern"],  # A-1, B-2 형식으로 출력
            "category_main": threats["primary_category"],  # A, B, C
            "pattern": threats.get("primary_pattern_name", "안전"),
            "warning": response_template["message"]
        }
    }


def get_response_for_level(risk_level: str) -> Dict[str, str]:
    """위험 레벨에 따른 응답 템플릿 반환"""
    data = _get_threat_data()
    return data["response_templates"].get(risk_level, data["response_templates"]["safe"])


# Legacy 호환성 함수들
def get_threat_categories() -> Dict[str, Any]:
    """Legacy: 이전 버전 호환용"""
    return get_all_categories()


def get_known_scam_scenarios() -> List[Dict]:
    """Legacy: 알려진 사기 시나리오 반환"""
    data = _get_threat_data()
    scenarios = []

    for cat_id, cat_info in data["categories"].items():
        for pattern_id, pattern in cat_info["patterns"].items():
            scenarios.append({
                "id": pattern_id,
                "name_ko": pattern["name_ko"],
                "category": cat_id,
                "sample_messages": pattern.get("sample_messages", [])
            })

    return scenarios


def calculate_threat_score(found_threats: List[Dict], url_analysis: Dict = None, scenario_match: Dict = None) -> Dict[str, Any]:
    """Legacy: 이전 버전 호환용 - detect_threats 사용 권장"""
    if not found_threats:
        return {
            "threat_score": 0,
            "threat_level": "SAFE",
            "is_likely_scam": False,
            "warning_message": "안전한 메시지입니다.",
            "recommended_action": "none"
        }

    # 새 함수 결과를 이전 형식으로 변환
    max_score = max(t.get("risk_score", 0) for t in found_threats)

    level_map = {
        "safe": "SAFE",
        "low": "SAFE",
        "medium": "SUSPICIOUS",
        "high": "DANGEROUS",
        "critical": "CRITICAL"
    }

    data = _get_threat_data()
    risk_level = _get_risk_level(max_score, data)

    return {
        "threat_score": max_score,
        "threat_level": level_map.get(risk_level, "SAFE"),
        "is_likely_scam": max_score >= 60,
        "warning_message": data["response_templates"][risk_level]["message"],
        "recommended_action": data["response_templates"][risk_level]["action"]
    }


def match_scam_scenario(found_threats: List[Dict]) -> Dict[str, Any]:
    """Legacy: 시나리오 매칭 - 새 구조에서는 패턴 자체가 시나리오"""
    if not found_threats:
        return {
            "matched_scenario": None,
            "confidence": "none",
            "pattern_coverage": 0
        }

    primary = found_threats[0] if found_threats else None
    if primary:
        return {
            "matched_scenario": {
                "id": primary.get("id"),
                "name_ko": primary.get("pattern_name_ko", primary.get("name_ko", ""))
            },
            "confidence": "high" if primary.get("match_strength", 0) > 0.7 else "medium",
            "pattern_coverage": primary.get("match_strength", 0)
        }

    return {
        "matched_scenario": None,
        "confidence": "none",
        "pattern_coverage": 0
    }


def get_threat_response(threat_level: str) -> Dict[str, str]:
    """Legacy: 위협 레벨에 따른 응답 템플릿 반환"""
    level_map = {
        "SAFE": "safe",
        "SUSPICIOUS": "medium",
        "DANGEROUS": "high",
        "CRITICAL": "critical"
    }
    return get_response_for_level(level_map.get(threat_level, "safe"))
