"""
Action Policy - 위험도별 액션 정책 모듈
위험 레벨에 따른 구체적 행동 지침 제공

정책:
- UI 표시 방식
- 사용자 경고 메시지
- 차단/신고 버튼 활성화
- 추가 확인 절차
"""
from typing import Dict, Any, List
from enum import Enum


class ActionType(str, Enum):
    """액션 타입"""
    NONE = "none"                    # 아무 조치 없음
    INFO = "info"                    # 정보성 알림
    WARN = "warn"                    # 경고 표시
    STRONG_WARN = "strong_warn"      # 강력 경고
    BLOCK_RECOMMEND = "block_recommend"  # 차단 권장
    BLOCK_AND_REPORT = "block_and_report"  # 차단 및 신고


# 위험도별 액션 정책
ACTION_POLICIES = {
    "SAFE": {
        "action_type": ActionType.NONE,
        "ui_config": {
            "show_warning": False,
            "warning_color": None,
            "show_block_button": False,
            "show_report_button": False
        },
        "user_message": None,
        "detailed_message": "안전한 메시지입니다.",
        "recommended_steps": []
    },
    "LOW": {
        "action_type": ActionType.INFO,
        "ui_config": {
            "show_warning": False,
            "warning_color": None,
            "show_block_button": False,
            "show_report_button": False
        },
        "user_message": None,
        "detailed_message": "특별한 위험 요소가 감지되지 않았습니다.",
        "recommended_steps": []
    },
    "MEDIUM": {
        "action_type": ActionType.WARN,
        "ui_config": {
            "show_warning": True,
            "warning_color": "#FFA726",  # Orange
            "warning_icon": "warning",
            "show_block_button": True,
            "show_report_button": False
        },
        "user_message": "주의가 필요한 메시지입니다",
        "detailed_message": "이 메시지에 의심스러운 패턴이 감지되었습니다. 발신자를 확인하세요.",
        "recommended_steps": [
            "발신자가 실제 아는 사람인지 확인하세요",
            "개인정보나 금융정보를 공유하지 마세요",
            "의심스러우면 전화로 직접 확인하세요"
        ]
    },
    "HIGH": {
        "action_type": ActionType.STRONG_WARN,
        "ui_config": {
            "show_warning": True,
            "warning_color": "#FF5252",  # Red
            "warning_icon": "error",
            "show_block_button": True,
            "show_report_button": True,
            "blur_message": False
        },
        "user_message": "위험! 주의가 필요합니다",
        "detailed_message": "피싱 또는 사기 메시지의 특징이 감지되었습니다. 절대 링크를 클릭하거나 정보를 제공하지 마세요.",
        "recommended_steps": [
            "링크를 클릭하지 마세요",
            "개인정보/금융정보를 절대 제공하지 마세요",
            "발신자에게 직접 전화하여 확인하세요",
            "의심스러우면 차단하세요"
        ]
    },
    "CRITICAL": {
        "action_type": ActionType.BLOCK_AND_REPORT,
        "ui_config": {
            "show_warning": True,
            "warning_color": "#D32F2F",  # Dark Red
            "warning_icon": "dangerous",
            "show_block_button": True,
            "show_report_button": True,
            "blur_message": True,  # 메시지 내용 블러 처리
            "require_confirmation": True  # 메시지 보기 전 확인 필요
        },
        "user_message": "사기/피싱 의심 메시지입니다!",
        "detailed_message": "이 메시지는 보이스피싱 또는 사기 메시지로 강력히 의심됩니다. 절대 응답하지 마시고 차단 및 신고를 권장합니다.",
        "recommended_steps": [
            "절대 응답하지 마세요",
            "어떤 정보도 제공하지 마세요",
            "링크를 클릭하지 마세요",
            "즉시 차단하세요",
            "경찰청(112) 또는 금융감독원(1332)에 신고하세요"
        ],
        "emergency_contacts": [
            {"name": "경찰청", "number": "112"},
            {"name": "금융감독원", "number": "1332"},
            {"name": "사이버범죄신고", "number": "182"}
        ]
    }
}


# 시나리오별 특수 정책
SCENARIO_POLICIES = {
    "family_impersonate": {
        "override_action": ActionType.BLOCK_AND_REPORT,
        "special_message": "가족을 사칭하는 메시지입니다!",
        "verification_prompt": "가족에게 직접 전화하여 확인하세요. 절대 송금하지 마세요!",
        "additional_steps": [
            "실제 가족의 원래 번호로 직접 전화하세요",
            "화상통화로 본인 확인을 요청하세요"
        ]
    },
    "authority_impersonate": {
        "override_action": ActionType.BLOCK_AND_REPORT,
        "special_message": "수사기관을 사칭하는 메시지입니다!",
        "verification_prompt": "검찰/경찰은 메신저로 수사 연락을 하지 않습니다!",
        "additional_steps": [
            "실제 수사기관(경찰 112)에 직접 확인하세요",
            "절대 계좌이체나 현금 인출을 하지 마세요"
        ]
    },
    "investment_scam": {
        "override_action": ActionType.BLOCK_AND_REPORT,
        "special_message": "투자 사기 의심 메시지입니다!",
        "verification_prompt": "고수익 보장 투자는 사기입니다!",
        "additional_steps": [
            "금융감독원(1332)에서 업체를 조회하세요",
            "원금 보장은 불법입니다 - 의심하세요"
        ]
    }
}


def get_action_policy(risk_level: str, scenario: str = None) -> Dict[str, Any]:
    """
    위험도별 액션 정책 조회

    Args:
        risk_level: 위험 레벨 (LOW/MEDIUM/HIGH/CRITICAL)
        scenario: 시나리오 ID (선택)

    Returns:
        action_type: 액션 타입
        ui_config: UI 설정
        user_message: 사용자 메시지
        detailed_message: 상세 메시지
        recommended_steps: 권장 조치 목록
        scenario_override: 시나리오 특수 정책 (있는 경우)
    """
    # 기본 정책 조회
    base_policy = ACTION_POLICIES.get(risk_level, ACTION_POLICIES["LOW"]).copy()

    # 시나리오 특수 정책 적용
    if scenario and scenario in SCENARIO_POLICIES:
        scenario_policy = SCENARIO_POLICIES[scenario]
        base_policy["scenario_override"] = scenario_policy

        # 시나리오 정책이 더 강하면 오버라이드
        if scenario_policy.get("override_action"):
            base_policy["action_type"] = scenario_policy["override_action"]

        if scenario_policy.get("special_message"):
            base_policy["user_message"] = scenario_policy["special_message"]

        if scenario_policy.get("additional_steps"):
            base_policy["recommended_steps"].extend(scenario_policy["additional_steps"])

    return base_policy


def get_combined_policy(
    text_risk: str,
    scam_check_result: Dict = None,
    sender_analysis: Dict = None,
    scenario_match: str = None
) -> Dict[str, Any]:
    """
    여러 분석 결과를 종합한 최종 정책 결정

    Args:
        text_risk: 텍스트 분석 위험도
        scam_check_result: 사기 신고 DB 조회 결과
        sender_analysis: 발신자 분석 결과
        scenario_match: 매칭된 시나리오

    Returns:
        final_risk_level: 최종 위험 레벨
        policy: 적용할 정책
        risk_factors: 위험 요소 목록
        total_risk_score: 종합 위험 점수
    """
    risk_scores = {
        "LOW": 10,
        "MEDIUM": 40,
        "HIGH": 70,
        "CRITICAL": 100
    }

    # 기본 점수
    total_score = risk_scores.get(text_risk, 10)
    risk_factors = []

    # 사기 신고 DB 결과 반영
    if scam_check_result and scam_check_result.get("has_reported_identifier"):
        scam_score = scam_check_result.get("max_risk_score", 0)
        total_score = max(total_score, scam_score)
        risk_factors.append({
            "source": "scam_db",
            "description": "신고된 계좌/번호가 포함되어 있습니다",
            "score_impact": scam_score
        })

    # 발신자 분석 결과 반영
    if sender_analysis:
        adjustment = sender_analysis.get("risk_adjustment", 0)
        total_score += adjustment
        if adjustment > 0:
            risk_factors.append({
                "source": "sender_analysis",
                "description": sender_analysis.get("warning_message", "발신자 신뢰도 낮음"),
                "score_impact": adjustment
            })

    # 점수 → 레벨 변환
    if total_score >= 90:
        final_level = "CRITICAL"
    elif total_score >= 60:
        final_level = "HIGH"
    elif total_score >= 30:
        final_level = "MEDIUM"
    else:
        final_level = "LOW"

    # 정책 조회
    policy = get_action_policy(final_level, scenario_match)

    return {
        "final_risk_level": final_level,
        "policy": policy,
        "risk_factors": risk_factors,
        "total_risk_score": min(100, max(0, total_score))
    }


def format_warning_for_ui(policy: Dict) -> Dict[str, Any]:
    """
    프론트엔드 UI용 경고 데이터 포맷

    Args:
        policy: get_action_policy() 결과

    Returns:
        프론트엔드에서 바로 사용할 수 있는 형태로 변환
    """
    ui_config = policy.get("ui_config", {})

    return {
        "show": ui_config.get("show_warning", False),
        "type": policy.get("action_type", ActionType.NONE),
        "color": ui_config.get("warning_color"),
        "icon": ui_config.get("warning_icon"),
        "title": policy.get("user_message"),
        "description": policy.get("detailed_message"),
        "steps": policy.get("recommended_steps", []),
        "buttons": {
            "block": ui_config.get("show_block_button", False),
            "report": ui_config.get("show_report_button", False)
        },
        "blur_content": ui_config.get("blur_message", False),
        "require_confirmation": ui_config.get("require_confirmation", False),
        "emergency_contacts": policy.get("emergency_contacts", [])
    }
