"""
Incoming Agent - 안심 가드 Agent
수신 메시지의 피싱/사기 위협을 탐지하고 사용자를 보호

v3.1 - 4단계 완전 분석 파이프라인 (category 필드 포함)

4단계 분석 Flow:
1. 텍스트 패턴 분석 (위협 감지, URL 분석, 시나리오 매칭)
2. 사기 신고 DB 조회 (계좌번호/전화번호)
3. 발신자 신뢰도 분석 (대화관계 조회)
4. 정책 기반 최종 판정 (액션 정책)

MCP 도구:
- scan_threats: 위협 패턴 스캔
- scan_urls: URL 분석
- check_scam_scenario: 시나리오 매칭
- check_reported_scam: 신고 DB 조회
- get_sender_trust: 발신자 신뢰도
- get_action_policy_for_risk: 액션 정책
"""
from .base import BaseAgent
from ..core.models import RiskLevel, AnalysisResponse
from ..core.threat_matcher import analyze_incoming_message


class IncomingAgent(BaseAgent):
    """안심 가드 Agent - 수신 메시지 위협 탐지 (4단계 분석)"""

    @property
    def name(self) -> str:
        return "incoming"

    def analyze(
        self,
        text: str,
        sender_id: int = None,
        user_id: int = None,
        use_ai: bool = True,
        **kwargs
    ) -> AnalysisResponse:
        """
        수신 메시지 위협 분석 (4단계 파이프라인)

        Args:
            text: 분석할 메시지
            sender_id: 발신자 ID (선택, 3단계 분석용)
            user_id: 수신자 ID (선택, 3단계 분석용)
            use_ai: LLM 정밀 분석 활성화 (기본: True)

        Returns:
            AnalysisResponse: 분석 결과
        """
        print(f"[IncomingAgent] 4단계 분석 시작: text={text[:50]}...")

        # 4단계 완전 분석
        result = self._analyze_4_stages(text, user_id, sender_id, use_ai)
        return self._convert_full_result_to_response(result)

    def _analyze_4_stages(
        self,
        text: str,
        user_id: int = None,
        sender_id: int = None,
        use_ai: bool = True
    ) -> dict:
        """
        4단계 완전 분석 파이프라인

        Stage 1: 텍스트 패턴 분석
        Stage 2: 사기 신고 DB 조회
        Stage 3: 발신자 신뢰도 분석
        Stage 4: 정책 기반 최종 판정
        """
        from ..core.scam_checker import check_scam_in_message
        from ..core.conversation_analyzer import analyze_sender_risk
        from ..core.action_policy import get_combined_policy, format_warning_for_ui

        # ========== Stage 1: 텍스트 패턴 분석 ==========
        print("[IncomingAgent] Stage 1: 텍스트 패턴 분석...")

        # Rule-based 분석 먼저 수행 (항상)
        stage1 = analyze_incoming_message(text)
        # analyze_incoming_message는 risk_level을 반환 (safe/low/medium/high/critical)
        risk_level_raw = stage1.get("final_assessment", {}).get("risk_level", "safe")
        # 소문자 → 대문자 변환 (SAFE → safe 호환)
        level_to_threat = {
            "safe": "SAFE",
            "low": "SAFE",
            "medium": "SUSPICIOUS",
            "high": "DANGEROUS",
            "critical": "CRITICAL"
        }
        threat_level = level_to_threat.get(risk_level_raw.lower(), "SAFE") if isinstance(risk_level_raw, str) else "SAFE"
        print(f"[IncomingAgent] Stage 1 Rule-based: risk_level={risk_level_raw} → threat_level={threat_level}")
        print(f"[IncomingAgent] Stage 1 결과: threat_level={threat_level}")

        # ========== Stage 2: 사기 신고 DB 조회 ==========
        print("[IncomingAgent] Stage 2: 사기 신고 DB 조회...")
        stage2 = check_scam_in_message(text)
        print(f"[IncomingAgent] Stage 2 결과: has_reported={stage2.get('has_reported_identifier')}")

        # ========== Stage 3: 발신자 신뢰도 분석 ==========
        stage3 = None
        if user_id and sender_id:
            print(f"[IncomingAgent] Stage 3: 발신자 신뢰도 분석 (user={user_id}, sender={sender_id})...")
            stage3 = analyze_sender_risk(user_id, sender_id, text)
            print(f"[IncomingAgent] Stage 3 결과: trust_level={stage3.get('sender_trust', {}).get('trust_level')}")
        else:
            print("[IncomingAgent] Stage 3: 스킵 (user_id/sender_id 없음)")

        # ========== Stage 4: 정책 기반 최종 판정 ==========
        print("[IncomingAgent] Stage 4: 정책 기반 최종 판정...")

        # 시나리오 매칭 확인
        scenario_match = None
        if stage1.get("scenario_match", {}).get("matched_scenario"):
            scenario_match = stage1["scenario_match"]["matched_scenario"].get("id")

        # threat_level → risk_level 변환 (action_policy가 기대하는 형식)
        level_convert = {
            "SAFE": "LOW",
            "SUSPICIOUS": "MEDIUM",
            "DANGEROUS": "HIGH",
            "CRITICAL": "CRITICAL"
        }
        risk_level_for_policy = level_convert.get(threat_level, "LOW")

        stage4 = get_combined_policy(
            text_risk=risk_level_for_policy,
            scam_check_result=stage2,
            sender_analysis=stage3,
            scenario_match=scenario_match
        )

        final_level = stage4["final_risk_level"]
        print(f"[IncomingAgent] Stage 4 결과: final_risk_level={final_level}, score={stage4.get('total_risk_score')}")

        # 결과 통합
        return {
            "stage1_threat_detection": stage1,
            "stage2_scam_check": stage2,
            "stage3_sender_trust": stage3,
            "stage4_final_policy": stage4,
            "final_risk_level": final_level,
            "ui_warning": format_warning_for_ui(stage4["policy"])
        }

    def _convert_full_result_to_response(self, result: dict) -> AnalysisResponse:
        """4단계 분석 결과를 AnalysisResponse로 변환"""
        stage1 = result.get("stage1_threat_detection", {})
        stage2 = result.get("stage2_scam_check", {})
        stage3 = result.get("stage3_sender_trust")
        stage4 = result.get("stage4_final_policy", {})

        final_level = result.get("final_risk_level", "LOW")

        # RiskLevel 변환
        level_map = {
            "LOW": RiskLevel.LOW,
            "MEDIUM": RiskLevel.MEDIUM,
            "HIGH": RiskLevel.HIGH,
            "CRITICAL": RiskLevel.CRITICAL
        }
        risk_level = level_map.get(final_level, RiskLevel.LOW)

        # MECE 카테고리 정보 추출
        summary = stage1.get("summary", {})
        category = summary.get("category")  # A-1, B-2 등
        category_name = summary.get("pattern")  # 가족 사칭 (액정 파손) 등

        # 사기 확률 추출
        final_assessment = stage1.get("final_assessment", {})
        scam_probability = final_assessment.get("scam_probability", 0)

        # 이유 목록 생성
        reasons = []

        # Stage 1: 위협 감지 이유
        threat_detection = stage1.get("threat_detection", {})
        for threat in threat_detection.get("found_threats", [])[:2]:
            reasons.append(f"{threat.get('name_ko', '위협')} 패턴 감지")

        # 시나리오 매칭
        scenario = stage1.get("scenario_match", {})
        if scenario.get("matched_scenario"):
            reasons.append(f"'{scenario['matched_scenario'].get('name_ko', '')}' 시나리오와 일치")

        # Stage 2: 신고 DB 결과
        if stage2.get("has_reported_identifier"):
            if stage2.get("reported_accounts"):
                reasons.append("신고된 계좌번호가 포함되어 있습니다!")
            if stage2.get("reported_phones"):
                reasons.append("신고된 전화번호가 포함되어 있습니다!")

        # Stage 3: 발신자 신뢰도
        if stage3:
            warning = stage3.get("warning_message")
            if warning:
                reasons.append(warning)

        # 경고 메시지 추가
        assessment = stage1.get("final_assessment", {})
        warning_msg = assessment.get("warning_message", "")
        if warning_msg and warning_msg not in reasons:
            reasons.insert(0, warning_msg)

        # 이유가 없으면 기본 메시지
        if not reasons:
            if final_level == "LOW":
                reasons.append("안전한 메시지입니다.")
            else:
                reasons.append("위험 요소가 감지되었습니다.")

        # 권장 조치
        policy = stage4.get("policy", {})
        action_type = policy.get("action_type", "none")
        action_map = {
            "none": "표시",
            "info": "정보 표시",
            "warn": "주의 표시",
            "strong_warn": "강력 경고",
            "block_recommend": "차단 권장",
            "block_and_report": "차단 및 신고"
        }
        recommended_action = action_map.get(str(action_type), str(action_type))

        return AnalysisResponse(
            risk_level=risk_level,
            reasons=reasons,
            recommended_action=recommended_action,
            is_secret_recommended=False,
            category=category,
            category_name=category_name,
            scam_probability=scam_probability
        )

    # Legacy 메서드 (호환성 유지)
    def _analyze_rule_based(self, text: str) -> AnalysisResponse:
        """Rule-based 분석 (legacy)"""
        result = analyze_incoming_message(text)
        return self._convert_to_response(result)

    def _analyze_with_hybrid(self, text: str) -> AnalysisResponse:
        """Hybrid 분석 (legacy)"""
        try:
            from ..core.hybrid_threat_analyzer import hybrid_threat_analyze
            result = hybrid_threat_analyze(text, use_llm=True)
            return self._convert_to_response(result)
        except Exception as e:
            print(f"[IncomingAgent] Hybrid analysis error: {e}")
            return self._analyze_rule_based(text)

    def _convert_to_response(self, result: dict) -> AnalysisResponse:
        """Legacy 변환 메서드"""
        assessment = result.get("final_assessment", result)
        threat_level = assessment.get("threat_level", "SAFE")

        level_map = {
            "SAFE": RiskLevel.LOW,
            "SUSPICIOUS": RiskLevel.MEDIUM,
            "DANGEROUS": RiskLevel.HIGH,
            "CRITICAL": RiskLevel.CRITICAL
        }
        risk_level = level_map.get(threat_level, RiskLevel.LOW)

        reasons = []
        threat_detection = result.get("threat_detection", {})
        for threat in threat_detection.get("found_threats", [])[:3]:
            reasons.append(f"{threat.get('name_ko', '위협')} 패턴 감지")

        warning = assessment.get("warning_message", "")
        if warning:
            reasons.insert(0, warning)

        action = assessment.get("recommended_action", "none")
        action_map = {
            "none": "표시",
            "warn": "주의 표시",
            "block_recommended": "차단 권장",
            "block_and_report": "차단 및 신고"
        }

        return AnalysisResponse(
            risk_level=risk_level,
            reasons=reasons,
            recommended_action=action_map.get(action, action),
            is_secret_recommended=False
        )
