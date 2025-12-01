"""
Threat Matcher - threat_patterns.json 기반 피싱/사기 패턴 매칭
AI(Agent B)가 MCP 도구를 통해 호출하는 수신 메시지 분석 모듈
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache


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


def get_threat_categories() -> Dict[str, Any]:
    """
    MCP Tool: 모든 위협 카테고리 정보 반환
    AI가 어떤 종류의 위협이 있는지 파악하는 데 사용

    Returns:
        카테고리별 위협 패턴 목록
    """
    data = _get_threat_data()
    result = {}

    for cat_id, cat_info in data["threat_categories"].items():
        result[cat_id] = {
            "name_ko": cat_info["name_ko"],
            "description": cat_info["description"],
            "risk_weight": cat_info["risk_weight"],
            "patterns": [
                {
                    "id": p["id"],
                    "name_ko": p["name_ko"],
                    "risk_level": p["risk_level"]
                }
                for p in cat_info["patterns"]
            ]
        }

    return result


def get_known_scam_scenarios() -> List[Dict]:
    """
    MCP Tool: 알려진 사기 시나리오 반환
    전형적인 보이스피싱/스미싱 패턴

    Returns:
        시나리오 목록
    """
    data = _get_threat_data()
    scenarios = []

    for scam_type, scam_info in data["known_scam_patterns"].items():
        for scenario in scam_info["scenarios"]:
            scenarios.append({
                "id": scenario["id"],
                "name_ko": scenario["name_ko"],
                "pattern_sequence": scenario["pattern_sequence"],
                "typical_phrases": scenario["typical_phrases"]
            })

    return scenarios


def detect_threats(text: str) -> Dict[str, Any]:
    """
    MCP Tool: 텍스트에서 위협 패턴 감지
    키워드 + 정규식 기반으로 위협을 탐지

    Args:
        text: 분석할 수신 메시지

    Returns:
        {
            "found_threats": [{"id": "...", "category": "...", "name_ko": "...", "risk_level": "..."}],
            "categories_found": ["financial_scam", "impersonation"],
            "highest_risk": "CRITICAL",
            "matched_keywords": ["긴급", "송금"]
        }
    """
    data = _get_threat_data()
    found_threats = []
    categories_found = set()
    all_matched_keywords = []
    highest_risk = "LOW"

    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    text_lower = text.lower()

    for cat_id, cat_info in data["threat_categories"].items():
        for pattern in cat_info["patterns"]:
            matched = False
            matched_keywords = []

            # 정규식 패턴 체크
            if "regex" in pattern:
                try:
                    if re.search(pattern["regex"], text, re.IGNORECASE):
                        matched = True
                        matched_keywords.append(f"[regex:{pattern['id']}]")
                except re.error:
                    pass

            # 키워드 패턴 체크
            if "keywords" in pattern:
                found_keywords = [k for k in pattern["keywords"] if k in text]
                if found_keywords:
                    # context_keywords가 있으면 함께 체크
                    if "context_keywords" in pattern:
                        found_context = [k for k in pattern["context_keywords"] if k in text]
                        if found_context:
                            matched = True
                            matched_keywords.extend(found_keywords)
                            matched_keywords.extend(found_context)
                    else:
                        matched = True
                        matched_keywords.extend(found_keywords)

            if matched:
                found_threats.append({
                    "id": pattern["id"],
                    "category": cat_id,
                    "category_name_ko": cat_info["name_ko"],
                    "name_ko": pattern["name_ko"],
                    "risk_level": pattern["risk_level"],
                    "matched_keywords": matched_keywords
                })
                categories_found.add(cat_id)
                all_matched_keywords.extend(matched_keywords)

                if risk_order[pattern["risk_level"]] > risk_order[highest_risk]:
                    highest_risk = pattern["risk_level"]

    return {
        "found_threats": found_threats,
        "categories_found": list(categories_found),
        "highest_risk": highest_risk,
        "matched_keywords": list(set(all_matched_keywords)),
        "count": len(found_threats)
    }


def detect_urls(text: str) -> Dict[str, Any]:
    """
    MCP Tool: 텍스트에서 URL 감지 및 안전성 분석

    Args:
        text: 분석할 텍스트

    Returns:
        {
            "urls_found": [...],
            "suspicious_urls": [...],
            "safe_urls": [...],
            "risk_level": "HIGH"
        }
    """
    data = _get_threat_data()

    # URL 추출 정규식
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls_found = re.findall(url_pattern, text)

    # 단축 URL 패턴도 추가
    short_url_pattern = r'(?:bit\.ly|tinyurl\.com|goo\.gl|t\.co|is\.gd|v\.gd|me2\.do|vo\.la)/[\w]+'
    short_urls = re.findall(short_url_pattern, text, re.IGNORECASE)
    urls_found.extend([f"https://{u}" for u in short_urls])

    safe_domains = data.get("safe_patterns", {}).get("whitelist_domains", [])

    suspicious_urls = []
    safe_urls = []
    risk_level = "LOW"

    for url in urls_found:
        is_safe = False
        for safe_domain in safe_domains:
            if safe_domain in url:
                is_safe = True
                safe_urls.append(url)
                break

        if not is_safe:
            suspicious_urls.append(url)

            # IP 주소 URL 체크
            if re.search(r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url):
                risk_level = "HIGH"
            # 의심 도메인 체크
            elif re.search(r'kakao|naver|bank|gov', url, re.IGNORECASE) and not any(sd in url for sd in safe_domains):
                risk_level = "CRITICAL"
            elif risk_level == "LOW":
                risk_level = "MEDIUM"

    return {
        "urls_found": urls_found,
        "suspicious_urls": suspicious_urls,
        "safe_urls": safe_urls,
        "risk_level": risk_level if suspicious_urls else "LOW",
        "has_shortened_url": bool(short_urls)
    }


def match_scam_scenario(found_threats: List[Dict]) -> Dict[str, Any]:
    """
    MCP Tool: 감지된 위협들이 알려진 사기 시나리오와 매칭되는지 확인

    Args:
        found_threats: detect_threats()에서 반환된 found_threats

    Returns:
        {
            "matched_scenario": {"id": "...", "name_ko": "..."},
            "confidence": "high/medium/low",
            "pattern_coverage": 0.75
        }
    """
    data = _get_threat_data()
    threat_ids = {t["id"] for t in found_threats}

    best_match = None
    best_coverage = 0

    for scam_type, scam_info in data["known_scam_patterns"].items():
        for scenario in scam_info["scenarios"]:
            required_patterns = set(scenario["pattern_sequence"])
            matched = threat_ids.intersection(required_patterns)
            coverage = len(matched) / len(required_patterns) if required_patterns else 0

            if coverage > best_coverage:
                best_coverage = coverage
                best_match = {
                    "id": scenario["id"],
                    "name_ko": scenario["name_ko"],
                    "typical_phrases": scenario["typical_phrases"]
                }

    if best_match and best_coverage > 0:
        confidence = "high" if best_coverage >= 0.8 else "medium" if best_coverage >= 0.5 else "low"
        return {
            "matched_scenario": best_match,
            "confidence": confidence,
            "pattern_coverage": best_coverage
        }

    return {
        "matched_scenario": None,
        "confidence": "none",
        "pattern_coverage": 0
    }


def calculate_threat_score(
    found_threats: List[Dict],
    url_analysis: Dict = None,
    scenario_match: Dict = None
) -> Dict[str, Any]:
    """
    MCP Tool: 최종 위협 점수 계산

    Args:
        found_threats: detect_threats()에서 반환된 found_threats
        url_analysis: detect_urls()에서 반환된 결과 (옵션)
        scenario_match: match_scam_scenario()에서 반환된 결과 (옵션)

    Returns:
        {
            "threat_score": 150,
            "threat_level": "CRITICAL",
            "is_likely_scam": true,
            "warning_message": "피싱/사기 메시지로 의심됩니다!",
            "recommended_action": "block_and_report"
        }
    """
    data = _get_threat_data()
    scoring = data["risk_scoring"]

    # 기본 점수 계산
    total_score = 0
    for threat in found_threats:
        base = scoring["base_scores"].get(threat["risk_level"], 10)
        total_score += base

    # 여러 카테고리 감지 시 가중
    categories = {t["category"] for t in found_threats}
    if len(categories) > 1:
        total_score *= scoring["multipliers"]["multiple_categories"]

    # URL 분석 결과 반영
    if url_analysis:
        if url_analysis.get("suspicious_urls"):
            total_score *= scoring["multipliers"]["url_present"]
        # 인증정보 요청과 URL 조합
        if any(t["id"] == "credential_request" for t in found_threats):
            total_score *= scoring["multipliers"]["credential_request"]

    # 시나리오 매칭 반영
    if scenario_match and scenario_match.get("matched_scenario"):
        if scenario_match["confidence"] in ["high", "medium"]:
            total_score *= scoring["multipliers"]["known_scenario_match"]

    # 위협 레벨 결정
    thresholds = scoring["thresholds"]
    if total_score >= thresholds["CRITICAL"]["min"]:
        threat_level = "CRITICAL"
    elif total_score >= thresholds["DANGEROUS"]["min"]:
        threat_level = "DANGEROUS"
    elif total_score >= thresholds["SUSPICIOUS"]["min"]:
        threat_level = "SUSPICIOUS"
    else:
        threat_level = "SAFE"

    # 응답 템플릿
    response = data["response_templates"].get(threat_level, data["response_templates"]["SAFE"])

    return {
        "threat_score": round(total_score),
        "threat_level": threat_level,
        "is_likely_scam": threat_level in ["DANGEROUS", "CRITICAL"],
        "warning_message": response["message"],
        "recommended_action": response["action"],
        "categories_detected": list(categories),
        "threat_count": len(found_threats)
    }


def analyze_incoming_message(text: str) -> Dict[str, Any]:
    """
    MCP Tool: 수신 메시지 종합 분석 (원스톱)
    모든 분석을 한 번에 수행

    Args:
        text: 분석할 수신 메시지

    Returns:
        종합 분석 결과
    """
    # 1. 위협 패턴 감지
    threats = detect_threats(text)

    # 2. URL 분석
    urls = detect_urls(text)

    # 3. 시나리오 매칭
    scenario = match_scam_scenario(threats["found_threats"])

    # 4. 최종 점수 계산
    score = calculate_threat_score(
        threats["found_threats"],
        urls,
        scenario
    )

    return {
        "text": text[:100] + "..." if len(text) > 100 else text,
        "threat_detection": threats,
        "url_analysis": urls,
        "scenario_match": scenario,
        "final_assessment": score,
        "summary": {
            "threat_level": score["threat_level"],
            "is_likely_scam": score["is_likely_scam"],
            "warning": score["warning_message"],
            "action": score["recommended_action"]
        }
    }


def get_threat_response(threat_level: str) -> Dict[str, str]:
    """위협 레벨에 따른 응답 템플릿 반환"""
    data = _get_threat_data()
    return data["response_templates"].get(threat_level, data["response_templates"]["SAFE"])
