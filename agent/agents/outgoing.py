"""
Outgoing Agent - 안심 전송 Agent
발신 메시지의 민감정보를 감지하고 보호 조치를 제안

기능:
- Rule-based PII 감지 (기본)
- Kanana LLM + ReAct 패턴 (use_ai=True)
"""
import re
from typing import Dict, Any
from .base import BaseAgent
from ..core.models import RiskLevel, AnalysisResponse
from ..llm.kanana import LLMManager
from ..prompts.outgoing_agent import get_outgoing_system_prompt


class OutgoingAgent(BaseAgent):
    """안심 전송 Agent - 발신 메시지 민감정보 감지"""

    # PII 패턴 정의 (확장)
    PATTERNS = {
        "account": {
            "regex": r'\d{3}-\d{2,6}-\d{3,6}',
            "message": "계좌번호 패턴이 감지되었습니다.",
            "risk": RiskLevel.MEDIUM,
        },
        "resident_id": {
            "regex": r'\d{6}-[1-4]\d{6}',
            "message": "주민등록번호 패턴이 감지되었습니다.",
            "risk": RiskLevel.CRITICAL,
        },
        "phone": {
            "regex": r'01[016789]-?\d{3,4}-?\d{4}',
            "message": "전화번호가 포함되어 있습니다.",
            "risk": RiskLevel.LOW,
        },
        "card": {
            "regex": r'\d{4}-?\d{4}-?\d{4}-?\d{4}',
            "message": "신용카드번호 패턴이 감지되었습니다.",
            "risk": RiskLevel.HIGH,
        },
        "passport": {
            "regex": r'[A-Z]{1,2}\d{7,8}',  # 한국 여권: M12345678
            "message": "여권번호 패턴이 감지되었습니다.",
            "risk": RiskLevel.CRITICAL,
        },
        "driver_license": {
            "regex": r'\d{2}-\d{2}-\d{6}-\d{2}',  # 운전면허: 11-22-123456-78
            "message": "운전면허번호 패턴이 감지되었습니다.",
            "risk": RiskLevel.HIGH,
        },
        "foreigner_id": {
            "regex": r'\d{6}-[5-8]\d{6}',  # 외국인등록번호: 앞자리 5-8
            "message": "외국인등록번호 패턴이 감지되었습니다.",
            "risk": RiskLevel.CRITICAL,
        },
    }

    @property
    def name(self) -> str:
        return "outgoing"

    def analyze(self, text: str, use_ai: bool = True, **kwargs) -> AnalysisResponse:
        """
        발신 메시지 민감정보 분석 (2-Tier 방식)

        Tier 1: 빠른 Rule-based 필터링 (모든 메시지에 적용)
        Tier 2: LLM 정밀 분석 (의심되는 메시지에만 적용, use_ai=True일 때)

        Args:
            text: 분석할 메시지
            use_ai: LLM 정밀 분석 활성화 (기본: True)

        Returns:
            AnalysisResponse: 분석 결과
        """
        # Tier 1: 빠른 필터링 - 숫자 패턴이 있는지 체크
        if not self._has_suspicious_pattern(text):
            # 의심스러운 패턴 없음 → 바로 통과
            return AnalysisResponse(
                risk_level=RiskLevel.LOW,
                reasons=[],
                recommended_action="전송",
                is_secret_recommended=False
            )

        # Tier 2: 의심스러운 패턴 발견 → 정밀 분석
        if use_ai:
            return self._analyze_with_ai(text)
        else:
            return self._analyze_rule_based(text)

    def _has_suspicious_pattern(self, text: str) -> bool:
        """
        빠른 필터링: 민감정보가 의심되는 패턴이 있는지 체크
        - 숫자가 일정 길이 이상 연속되거나
        - "-"로 구분된 숫자 패턴이 있거나
        - 민감정보 관련 키워드가 있으면 True
        """
        import re

        # 숫자가 6자리 이상 연속 (하이픈 포함)
        if re.search(r'[\d-]{8,}', text):
            return True

        # 민감정보 관련 키워드
        sensitive_keywords = [
            '계좌', '통장', '카드', '번호',
            '주민', '등록', '여권', '면허',
            '외국인', '비밀번호', '인증',
            '송금', '이체', '입금'
        ]
        for keyword in sensitive_keywords:
            if keyword in text:
                return True

        return False

    def _analyze_rule_based(self, text: str) -> AnalysisResponse:
        """Rule-based 분석 (기존 방식)"""
        reasons = []
        risk_level = RiskLevel.LOW
        is_secret_recommended = False

        # 전화번호 먼저 찾아서 마스킹 (계좌번호와 구분하기 위해)
        phone_pattern = self.PATTERNS["phone"]["regex"]
        phone_matches = re.findall(phone_pattern, text)
        text_without_phones = re.sub(phone_pattern, "PHONE_MASKED", text)

        # 전화번호 감지 기록
        if phone_matches:
            reasons.append(self.PATTERNS["phone"]["message"])

        # 나머지 패턴 검사 (전화번호 제외된 텍스트에서)
        for pattern_name, pattern_info in self.PATTERNS.items():
            if pattern_name == "phone":
                continue  # 이미 처리됨

            if re.search(pattern_info["regex"], text_without_phones):
                reasons.append(pattern_info["message"])

                # 위험도 업그레이드 (더 높은 것으로)
                if self._compare_risk(pattern_info["risk"], risk_level) > 0:
                    risk_level = pattern_info["risk"]

                # 민감정보는 시크릿 전송 추천 (전화번호 제외)
                if pattern_name != "phone":
                    is_secret_recommended = True

        recommended_action = "전송"
        if is_secret_recommended:
            recommended_action = "시크릿 전송 추천"

        return AnalysisResponse(
            risk_level=risk_level,
            reasons=reasons,
            recommended_action=recommended_action,
            is_secret_recommended=is_secret_recommended
        )

    def _analyze_with_ai(self, text: str) -> AnalysisResponse:
        """Kanana LLM + ReAct 패턴으로 분석"""
        try:
            # LLM 인스턴스 가져오기
            llm = LLMManager.get("instruct")
            if not llm:
                print("[OutgoingAgent] LLM not available, falling back to rule-based")
                return self._analyze_rule_based(text)

            # 도구 정의
            tools = {
                "detect_pii": self._tool_detect_pii,
                "recommend_secret_mode": self._tool_recommend_secret_mode
            }

            # 시스템 프롬프트 가져오기
            system_prompt = get_outgoing_system_prompt()

            # LLM으로 분석
            result = llm.analyze_with_tools(
                user_message=text,
                system_prompt=system_prompt,
                tools=tools,
                max_iterations=3
            )

            # 결과를 AnalysisResponse로 변환
            risk_level_str = result.get("risk_level", "LOW").upper()
            risk_level = getattr(RiskLevel, risk_level_str, RiskLevel.LOW)

            return AnalysisResponse(
                risk_level=risk_level,
                reasons=result.get("reasons", []),
                recommended_action=result.get("recommended_action", "전송"),
                is_secret_recommended=result.get("is_secret_recommended", False)
            )

        except Exception as e:
            print(f"[OutgoingAgent] AI analysis error: {e}, falling back to rule-based")
            return self._analyze_rule_based(text)

    def _tool_detect_pii(self, text: str) -> Dict[str, Any]:
        """detect_pii 도구 - LLM이 호출하는 PII 감지 함수"""
        found_pii = []
        risk_level = "LOW"

        # 각 패턴 검사
        for pattern_name, pattern_info in self.PATTERNS.items():
            matches = re.findall(pattern_info["regex"], text)
            if matches:
                for match in matches:
                    found_pii.append(f"{pattern_name}:{match}")

                # 가장 높은 위험도로 업데이트
                pattern_risk = pattern_info["risk"].value
                if self._risk_value(pattern_risk) > self._risk_value(risk_level):
                    risk_level = pattern_risk

        return {
            "found_pii": found_pii,
            "risk_level": risk_level,
            "recommendations": ["시크릿 전송 권장"] if found_pii else []
        }

    def _tool_recommend_secret_mode(self, pii_types: list = None, risk_level: str = "LOW") -> Dict[str, Any]:
        """recommend_secret_mode 도구 - 시크릿 모드 추천 결정"""
        pii_types = pii_types or []

        # 민감한 정보 유형 체크
        sensitive_types = {"account", "resident_id", "card"}
        has_sensitive = any(pii in sensitive_types for pii in pii_types)

        # HIGH 이상이거나 민감정보 있으면 시크릿 추천
        should_use = has_sensitive or risk_level in ["HIGH", "CRITICAL"]

        return {
            "should_use_secret": should_use,
            "reason": "민감한 개인정보가 포함되어 있습니다." if should_use else "일반 전송 가능합니다."
        }

    def _risk_value(self, risk: str) -> int:
        """위험도를 숫자로 변환"""
        order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        return order.get(risk.upper(), 0)

    def _compare_risk(self, a: RiskLevel, b: RiskLevel) -> int:
        """위험도 비교 (a > b이면 양수)"""
        order = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }
        return order[a] - order[b]
