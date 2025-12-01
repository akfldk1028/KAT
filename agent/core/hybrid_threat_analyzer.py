"""
Hybrid Threat Analyzer - Smart Tiered Analysis
Agent B (안심 가드)용 수신 메시지 피싱/사기 감지

연구 기반 설계 (2024 최신 연구 반영):
- Tier 1: Rule-based 빠른 필터 (~1ms) - 정상 메시지 빠르게 통과
- Tier 2: Kanana Few-shot 분류 (~150ms) - 의심 메시지만 LLM 검증
- Tier 3: 결과 병합 - Rule + LLM 교차 검증

참고 연구:
- "Real-time Korean voice phishing detection" (Springer, 2021)
- "Attention-Based 1D CNN-BiLSTM for Korean Phishing" (MDPI, 2023)
- "NER with Key Tags for Korean Voice Phishing" (IEEE, 2024)
"""
from typing import Dict, Any, List, Optional
import json
import re
import time

from .threat_matcher import (
    detect_threats,
    detect_urls,
    match_scam_scenario,
    calculate_threat_score,
    analyze_incoming_message,
    get_threat_response
)


# ============================================================
# Kanana 최적화 경량 프롬프트 (Few-shot 기반)
# 연구 결과: 짧은 프롬프트 + Few-shot이 3B 모델에 효과적
# ============================================================

# 빠른 이진 분류용 (출력 토큰 최소화)
LLM_QUICK_CLASSIFY_PROMPT = """피싱/사기 메시지인지 판단하세요.

[피싱 예시]
- "엄마야 폰 고장나서 급하게 돈 보내줘" → 피싱 (가족사칭)
- "검찰입니다 계좌가 범죄에 연루됐습니다" → 피싱 (기관사칭)
- "bit.ly/abc 클릭해서 본인확인하세요" → 피싱 (링크유도)
- "축하합니다 당첨! 계좌번호 알려주세요" → 피싱 (정보탈취)
- "저금리 무담보 대출 즉시 승인" → 피싱 (대출사기)

[정상 예시]
- "오늘 저녁 뭐 먹을까?" → 정상
- "내일 회의 10시에 하자" → 정상
- "주말에 영화 볼래?" → 정상
- "생일 축하해!" → 정상

메시지: "{text}"
판단 (피싱/정상):"""


# 상세 분석용 (Rule이 놓친 위협 탐지)
LLM_DETAILED_PROMPT = """수신 메시지를 분석하세요.

[피싱 패턴]
1. 가족사칭: 폰고장, 새번호, 급한돈
2. 기관사칭: 검찰, 경찰, 금감원, 수사
3. 링크유도: 단축URL, 의심도메인
4. 정보탈취: 비밀번호, OTP, 계좌번호
5. 심리압박: 긴급, 체포, 동결

메시지: "{text}"

JSON으로 답하세요:
{{"판단":"피싱/정상","유형":"","근거":"","위험도":"SAFE/SUSPICIOUS/DANGEROUS/CRITICAL"}}"""


class HybridThreatAnalyzer:
    """
    Smart Tiered 위협 분석기 (Kanana 3B 최적화)

    Tier 1: Rule-based (~1ms) - 명확한 케이스 빠르게 처리
    Tier 2: Kanana Few-shot (~150ms) - 의심 메시지만 LLM 검증
    Tier 3: 결과 병합 - 교차 검증으로 정확도 향상

    핵심 최적화:
    - 정상 메시지 90%+는 LLM 호출 없이 처리 (속도)
    - 짧은 프롬프트 + Few-shot (추론 시간 단축)
    - 조건부 LLM 호출 (SAFE면 스킵)
    """

    def __init__(self):
        self.llm = None
        self._llm_initialized = False
        # 성능 통계
        self.stats = {
            "total_calls": 0,
            "llm_calls": 0,
            "llm_skipped": 0,
            "avg_time_ms": 0
        }

    def _get_llm(self):
        """LLM 인스턴스 가져오기 (Lazy Loading)"""
        if not self._llm_initialized:
            try:
                from ..llm.kanana import LLMManager
                self.llm = LLMManager.get("instruct")
                self._llm_initialized = True
            except Exception as e:
                print(f"[HybridThreatAnalyzer] LLM 로드 실패: {e}")
                self._llm_initialized = True
        return self.llm

    def analyze(self, text: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        Smart Tiered 위협 분석 수행

        Args:
            text: 분석할 수신 메시지
            use_llm: LLM 분석 사용 여부

        Returns:
            통합 분석 결과
        """
        start_time = time.time()
        self.stats["total_calls"] += 1

        # ========================================
        # Tier 1: Rule-based 분석 (~1ms)
        # ========================================
        rule_result = self._rule_based_analyze(text)
        rule_level = rule_result.get("threat_level", "SAFE")

        # LLM 사용 안함
        if not use_llm:
            rule_result["analysis_time_ms"] = (time.time() - start_time) * 1000
            rule_result["llm_used"] = False
            return rule_result

        # ========================================
        # Smart Skip: SAFE면 LLM 호출 안함 (최적화 핵심)
        # ========================================
        if rule_level == "SAFE":
            self.stats["llm_skipped"] += 1
            rule_result["analysis_time_ms"] = (time.time() - start_time) * 1000
            rule_result["llm_used"] = False
            rule_result["skip_reason"] = "Rule-based SAFE, LLM 스킵"
            return rule_result

        # ========================================
        # Tier 2: Kanana LLM 분석 (의심 메시지만)
        # ========================================
        llm = self._get_llm()
        if not llm:
            rule_result["analysis_time_ms"] = (time.time() - start_time) * 1000
            rule_result["llm_used"] = False
            return rule_result

        self.stats["llm_calls"] += 1

        # 위험도에 따라 프롬프트 선택
        if rule_level in ["DANGEROUS", "CRITICAL"]:
            # 상세 분석 (이미 위험 감지됨)
            llm_result = self._llm_detailed_analyze(text)
        else:
            # 빠른 분류 (SUSPICIOUS 케이스)
            llm_result = self._llm_quick_classify(text)

        # ========================================
        # Tier 3: 결과 병합
        # ========================================
        merged = self._merge_results(rule_result, llm_result)
        merged["analysis_time_ms"] = (time.time() - start_time) * 1000
        merged["llm_used"] = True

        return merged

    def _rule_based_analyze(self, text: str) -> Dict[str, Any]:
        """Rule-based 위협 분석 (~1ms)"""
        result = analyze_incoming_message(text)

        return {
            "method": "rule_based",
            "threat_level": result["final_assessment"]["threat_level"],
            "threat_score": result["final_assessment"]["threat_score"],
            "is_likely_scam": result["final_assessment"]["is_likely_scam"],
            "detected_threats": result["threat_detection"]["found_threats"],
            "url_analysis": result["url_analysis"],
            "scenario_match": result["scenario_match"],
            "warning_message": result["final_assessment"]["warning_message"],
            "recommended_action": result["final_assessment"]["recommended_action"]
        }

    def _llm_quick_classify(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Kanana Few-shot 빠른 분류 (~150ms)
        - 짧은 프롬프트로 이진 분류
        - 출력 토큰 최소화
        """
        llm = self._get_llm()
        if not llm:
            return None

        try:
            prompt = LLM_QUICK_CLASSIFY_PROMPT.format(text=text)
            response = llm.analyze(text=prompt, system_prompt="")

            # 응답 파싱 (피싱/정상)
            response_lower = response.strip().lower()

            if "피싱" in response_lower or "phishing" in response_lower:
                # 피싱 유형 추출 시도
                threat_type = "unknown"
                if "가족" in response_lower:
                    threat_type = "family_impersonate"
                elif "기관" in response_lower or "검찰" in response_lower:
                    threat_type = "authority_impersonate"
                elif "링크" in response_lower:
                    threat_type = "link_phishing"
                elif "정보" in response_lower or "탈취" in response_lower:
                    threat_type = "info_extraction"
                elif "대출" in response_lower:
                    threat_type = "loan_offer"

                return {
                    "method": "llm_quick",
                    "threat_level": "DANGEROUS",  # LLM이 피싱으로 판단
                    "is_likely_scam": True,
                    "detected_threats": [{
                        "id": threat_type,
                        "name_ko": "LLM 피싱 감지",
                        "source": "llm",
                        "raw_response": response[:100]
                    }],
                    "llm_raw_response": response
                }
            else:
                return {
                    "method": "llm_quick",
                    "threat_level": "SAFE",
                    "is_likely_scam": False,
                    "detected_threats": [],
                    "llm_raw_response": response
                }

        except Exception as e:
            print(f"[HybridThreatAnalyzer] LLM 빠른분류 오류: {e}")
            return None

    def _llm_detailed_analyze(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Kanana 상세 분석 (~200ms)
        - 이미 위험으로 판정된 케이스
        - 추가 위협 탐지 및 근거 수집
        """
        llm = self._get_llm()
        if not llm:
            return None

        try:
            prompt = LLM_DETAILED_PROMPT.format(text=text)
            response = llm.analyze(text=prompt, system_prompt="")

            result = self._parse_llm_json(response)
            if result:
                result["method"] = "llm_detailed"
                return result

            # JSON 파싱 실패 시 텍스트 분석
            return self._parse_llm_text(response)

        except Exception as e:
            print(f"[HybridThreatAnalyzer] LLM 상세분석 오류: {e}")
            return None

    def _parse_llm_json(self, response: str) -> Optional[Dict[str, Any]]:
        """LLM JSON 응답 파싱"""
        # JSON 블록 찾기
        patterns = [
            r'\{[^{}]*\}',
            r'```json\s*(\{[^`]*\})\s*```',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match if isinstance(match, str) else match)

                    # 한글 키 처리
                    threat_level = data.get("위험도", data.get("threat_level", "SUSPICIOUS"))
                    is_phishing = data.get("판단", "").lower() in ["피싱", "phishing"]

                    return {
                        "threat_level": threat_level if threat_level in ["SAFE", "SUSPICIOUS", "DANGEROUS", "CRITICAL"] else "SUSPICIOUS",
                        "is_likely_scam": is_phishing,
                        "detected_threats": [{
                            "id": data.get("유형", "unknown"),
                            "name_ko": data.get("유형", "LLM 감지"),
                            "evidence": data.get("근거", ""),
                            "source": "llm"
                        }] if is_phishing else [],
                        "llm_reasoning": data.get("근거", "")
                    }
                except json.JSONDecodeError:
                    continue

        return None

    def _parse_llm_text(self, response: str) -> Optional[Dict[str, Any]]:
        """LLM 텍스트 응답 파싱 (JSON 실패 시)"""
        response_lower = response.lower()

        is_phishing = "피싱" in response_lower or "사기" in response_lower or "위험" in response_lower

        if "critical" in response_lower:
            level = "CRITICAL"
        elif "dangerous" in response_lower or "위험" in response_lower:
            level = "DANGEROUS"
        elif "suspicious" in response_lower or "의심" in response_lower:
            level = "SUSPICIOUS"
        else:
            level = "SUSPICIOUS" if is_phishing else "SAFE"

        return {
            "method": "llm_text_parse",
            "threat_level": level,
            "is_likely_scam": is_phishing,
            "detected_threats": [{
                "id": "llm_detected",
                "name_ko": "LLM 텍스트 분석",
                "source": "llm"
            }] if is_phishing else [],
            "llm_raw_response": response[:200]
        }

    def _merge_results(
        self,
        rule_result: Dict[str, Any],
        llm_result: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Rule-based와 LLM 결과 병합

        병합 규칙:
        1. 위협 레벨: 더 높은 위험도 선택
        2. 감지된 위협: Union
        3. 경고 메시지: 더 위험한 쪽 선택
        """
        if not llm_result:
            return rule_result

        level_order = {"SAFE": 0, "SUSPICIOUS": 1, "DANGEROUS": 2, "CRITICAL": 3}

        rule_level = rule_result.get("threat_level", "SAFE")
        llm_level = llm_result.get("threat_level", "SAFE")

        # 최대 위험도 선택
        if level_order.get(llm_level, 0) > level_order.get(rule_level, 0):
            final_level = llm_level
            final_warning = llm_result.get("warning_message", "")
            final_action = llm_result.get("recommended_action", "none")
            primary_source = "llm"
        else:
            final_level = rule_level
            final_warning = rule_result.get("warning_message", "")
            final_action = rule_result.get("recommended_action", "none")
            primary_source = "rule"

        # 위협 목록 병합
        rule_threats = rule_result.get("detected_threats", [])
        llm_threats = llm_result.get("detected_threats", [])

        # LLM 위협을 Rule 형식으로 변환
        llm_threats_normalized = []
        for t in llm_threats:
            llm_threats_normalized.append({
                "id": t.get("type", "unknown"),
                "category": "llm_detected",
                "category_name_ko": "LLM 감지",
                "name_ko": t.get("type_ko", t.get("type", "알수없음")),
                "risk_level": self._confidence_to_risk(t.get("confidence", "medium")),
                "source": "llm",
                "evidence": t.get("evidence", "")
            })

        # 중복 제거 병합
        merged_threats = list(rule_threats)
        existing_ids = {t.get("id", "") for t in rule_threats}

        for t in llm_threats_normalized:
            if t.get("id", "") not in existing_ids:
                merged_threats.append(t)
                existing_ids.add(t.get("id", ""))

        # 점수 재계산 (더 많은 위협 발견 시)
        threat_score = rule_result.get("threat_score", 0)
        if len(merged_threats) > len(rule_threats):
            # LLM이 추가 위협 발견
            threat_score = int(threat_score * 1.3)

        return {
            "method": "hybrid",
            "threat_level": final_level,
            "threat_score": threat_score,
            "is_likely_scam": final_level in ["DANGEROUS", "CRITICAL"],
            "detected_threats": merged_threats,
            "rule_threats_count": len(rule_threats),
            "llm_threats_count": len(llm_threats),
            "total_threats_count": len(merged_threats),
            "manipulation_tactics": llm_result.get("manipulation_tactics", []),
            "warning_message": final_warning,
            "recommended_action": final_action,
            "llm_reasoning": llm_result.get("analysis_reasoning", ""),
            "url_analysis": rule_result.get("url_analysis"),
            "scenario_match": rule_result.get("scenario_match"),
            "primary_source": primary_source
        }

    def _confidence_to_risk(self, confidence: str) -> str:
        """LLM confidence를 risk level로 변환"""
        mapping = {
            "high": "CRITICAL",
            "medium": "HIGH",
            "low": "MEDIUM"
        }
        return mapping.get(confidence, "MEDIUM")


# 싱글톤 인스턴스
_threat_analyzer_instance: Optional[HybridThreatAnalyzer] = None


def get_hybrid_threat_analyzer() -> HybridThreatAnalyzer:
    """Hybrid 위협 분석기 싱글톤 인스턴스 반환"""
    global _threat_analyzer_instance
    if _threat_analyzer_instance is None:
        _threat_analyzer_instance = HybridThreatAnalyzer()
    return _threat_analyzer_instance


def hybrid_threat_analyze(text: str, use_llm: bool = True) -> Dict[str, Any]:
    """
    Hybrid 위협 분석 수행 (편의 함수)

    Args:
        text: 분석할 수신 메시지
        use_llm: LLM 분석 사용 여부

    Returns:
        분석 결과
    """
    analyzer = get_hybrid_threat_analyzer()
    return analyzer.analyze(text, use_llm=use_llm)
