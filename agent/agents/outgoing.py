"""
Outgoing Agent - 안심 전송 Agent
발신 메시지의 민감정보를 감지하고 보호 조치를 제안
"""
import re
from .base import BaseAgent
from ..core.models import RiskLevel, AnalysisResponse


class OutgoingAgent(BaseAgent):
    """안심 전송 Agent - 발신 메시지 민감정보 감지"""

    # PII 패턴 정의
    PATTERNS = {
        "account": {
            "regex": r'\d{3}-\d{2,6}-\d{3,6}',
            "message": "계좌번호 패턴이 감지되었습니다.",
            "risk": RiskLevel.MEDIUM,
        },
        "resident_id": {
            "regex": r'\d{6}-[1-4]\d{6}',
            "message": "주민등록번호 패턴이 감지되었습니다.",
            "risk": RiskLevel.HIGH,
        },
        "phone": {
            "regex": r'01[016789]-\d{3,4}-\d{4}',
            "message": "전화번호가 포함되어 있습니다.",
            "risk": RiskLevel.LOW,
        },
        "card": {
            "regex": r'\d{4}-\d{4}-\d{4}-\d{4}',
            "message": "신용카드번호 패턴이 감지되었습니다.",
            "risk": RiskLevel.HIGH,
        },
    }

    @property
    def name(self) -> str:
        return "outgoing"

    def analyze(self, text: str, **kwargs) -> AnalysisResponse:
        """발신 메시지 민감정보 분석"""
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

                # 계좌, 주민번호, 카드번호는 시크릿 전송 추천
                if pattern_name in ["account", "resident_id", "card"]:
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

    def _compare_risk(self, a: RiskLevel, b: RiskLevel) -> int:
        """위험도 비교 (a > b이면 양수)"""
        order = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }
        return order[a] - order[b]
