"""
Incoming Agent - 안심 가드 Agent
수신 메시지의 피싱/사기 위협을 탐지하고 사용자를 보호
"""
from .base import BaseAgent
from ..core.models import RiskLevel, AnalysisResponse


class IncomingAgent(BaseAgent):
    """안심 가드 Agent - 수신 메시지 위협 탐지"""

    # 위협 패턴 정의
    IMPERSONATION_KEYWORDS = ["엄마", "아빠", "아들", "딸", "폰 고장", "액정 깨짐", "인증번호", "새 번호"]
    URGENT_KEYWORDS = ["급해", "빨리", "송금", "돈 좀", "계좌", "지금 당장"]
    PHISHING_INDICATORS = ["http", "www", "bit.ly", "goo.gl", "tinyurl"]

    @property
    def name(self) -> str:
        return "incoming"

    def analyze(self, text: str, sender_id: str = None, use_ai: bool = False, **kwargs) -> AnalysisResponse:
        """수신 메시지 위협 분석"""
        reasons = []
        risk_level = RiskLevel.LOW
        recommended_action = "표시"

        # 1. 가족 사칭 + 긴급 요청 패턴
        found_impersonation = [k for k in self.IMPERSONATION_KEYWORDS if k in text]
        found_urgent = [k for k in self.URGENT_KEYWORDS if k in text]

        if found_impersonation and found_urgent:
            reasons.append("가족 사칭 및 금전 요구 패턴이 감지되었습니다.")
            risk_level = RiskLevel.CRITICAL
            recommended_action = "차단 및 경고"
        elif found_impersonation:
            reasons.append("가족 사칭 의심 패턴이 감지되었습니다.")
            risk_level = RiskLevel.MEDIUM
            recommended_action = "주의 표시"
        elif found_urgent:
            reasons.append("송금 유도 패턴이 감지되었습니다.")
            risk_level = RiskLevel.MEDIUM
            recommended_action = "주의 표시"

        # 2. 피싱 링크 감지
        if any(indicator in text.lower() for indicator in self.PHISHING_INDICATORS):
            reasons.append("링크가 포함되어 있습니다. 출처를 확인하세요.")
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM
                recommended_action = "주의 표시"

        # 3. AI 분석 (옵션)
        if use_ai:
            ai_result = self._analyze_with_ai(text)
            if ai_result and not ai_result.get("is_safe", True):
                reasons.append(f"AI 보안 모델이 위험을 감지했습니다: {ai_result.get('category', 'Unknown')}")
                if risk_level == RiskLevel.LOW:
                    risk_level = RiskLevel.HIGH
                elif risk_level == RiskLevel.MEDIUM:
                    risk_level = RiskLevel.CRITICAL
                recommended_action = "강력 경고 및 차단 권장"

        return AnalysisResponse(
            risk_level=risk_level,
            reasons=reasons,
            recommended_action=recommended_action,
            is_secret_recommended=False
        )

    def _analyze_with_ai(self, text: str) -> dict:
        """Kanana Safeguard AI로 분석 (lazy loading)"""
        try:
            from ..llm.kanana import LLMManager
            safeguard = LLMManager.get("safeguard")
            if safeguard:
                return safeguard.classify_safety(user_prompt=text, assistant_prompt="")
        except Exception as e:
            print(f"[IncomingAgent] AI analysis failed: {e}")
        return None
