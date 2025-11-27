"""
MCP Tools for DualGuard Agent
발신/수신 메시지 분석 도구
"""

import re
from typing import Optional, List
from ..core.models import RiskLevel, AnalysisResult
from ..llm.kanana import LLMManager


# ============================================
# 패턴 정의
# ============================================

# 개인정보 패턴 (정규식)
PII_PATTERNS = {
    "주민등록번호": r"\d{6}[-\s]?\d{7}",
    "계좌번호": r"\d{3,4}[-\s]?\d{2,4}[-\s]?\d{4,6}[-\s]?\d{0,4}",
    "신용카드번호": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
    "전화번호": r"(010|011|016|017|018|019)[-\s]?\d{3,4}[-\s]?\d{4}",
    "이메일": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "여권번호": r"[A-Z]{1,2}\d{7,8}",
    "운전면허번호": r"\d{2}[-\s]?\d{2}[-\s]?\d{6}[-\s]?\d{2}",
}

# 위협 키워드 패턴
THREAT_KEYWORDS = {
    "긴급송금": ["급하게", "지금 바로", "빨리 보내", "당장", "즉시 송금", "긴급"],
    "가족사칭": ["엄마", "아빠", "아들", "딸", "폰 고장", "액정 깨", "새 번호", "번호 바꿨"],
    "금융사기": ["대출", "저금리", "승인", "한도", "보증금", "투자", "수익률", "원금보장"],
    "피싱링크": ["http://", "https://", "bit.ly", "클릭", "확인하세요", "링크"],
    "개인정보요구": ["비밀번호", "인증번호", "보안카드", "OTP", "계좌", "카드번호"],
}


# ============================================
# Rule-based 분석 함수
# ============================================

def detect_pii_patterns(text: str) -> List[str]:
    """텍스트에서 개인정보 패턴 감지"""
    detected = []
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, text):
            detected.append(pii_type)
    return detected


def detect_threat_keywords(text: str) -> List[str]:
    """텍스트에서 위협 키워드 감지"""
    detected = []
    for threat_type, keywords in THREAT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                detected.append(threat_type)
                break
    return detected


def calculate_risk_level(pii_count: int, threat_count: int) -> RiskLevel:
    """감지된 패턴 수에 따른 위험 수준 계산"""
    total = pii_count + threat_count

    if total == 0:
        return RiskLevel.SAFE
    elif total == 1:
        return RiskLevel.LOW
    elif total <= 3:
        return RiskLevel.MEDIUM
    elif total <= 5:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


# ============================================
# 분석 도구 (MCP Tool)
# ============================================

def analyze_outgoing(text: str, use_ai: bool = False) -> AnalysisResult:
    """
    안심 전송 - 발신 메시지 분석

    발신 메시지에서 개인정보(PII)를 감지합니다.
    민감정보가 포함된 경우 비밀채팅을 권장합니다.

    Args:
        text: 분석할 메시지 텍스트
        use_ai: True면 Kanana LLM 사용, False면 Rule-based

    Returns:
        AnalysisResult: 분석 결과
    """
    # Rule-based 분석 (항상 수행)
    detected_pii = detect_pii_patterns(text)
    risk_level = calculate_risk_level(len(detected_pii), 0)

    reasons = []
    for pii_type in detected_pii:
        reasons.append(f"{pii_type} 패턴 감지됨")

    # AI 분석 (옵션)
    if use_ai:
        instruct_model = LLMManager.get("instruct")
        if instruct_model:
            try:
                ai_result = instruct_model.analyze_text(text, analysis_type="pii")
                reasons.append(f"AI 분석: {ai_result[:200]}...")
            except Exception as e:
                reasons.append(f"AI 분석 실패: {str(e)}")

    # 권장 조치 결정
    if risk_level == RiskLevel.SAFE:
        recommended_action = "안전하게 전송 가능합니다."
        is_secret_recommended = False
    elif risk_level == RiskLevel.LOW:
        recommended_action = "민감정보가 포함되어 있을 수 있습니다. 확인 후 전송해주세요."
        is_secret_recommended = False
    elif risk_level == RiskLevel.MEDIUM:
        recommended_action = "개인정보가 감지되었습니다. 비밀채팅 사용을 권장합니다."
        is_secret_recommended = True
    else:  # HIGH, CRITICAL
        recommended_action = "중요 개인정보가 다수 감지되었습니다! 비밀채팅을 강력히 권장합니다."
        is_secret_recommended = True

    return AnalysisResult(
        risk_level=risk_level,
        reasons=reasons,
        recommended_action=recommended_action,
        is_secret_recommended=is_secret_recommended,
        detected_pii=detected_pii,
    )


def analyze_incoming(
    text: str,
    sender_id: Optional[str] = None,
    use_ai: bool = False
) -> AnalysisResult:
    """
    안심 가드 - 수신 메시지 분석

    수신 메시지에서 피싱, 스미싱, 사기 패턴을 감지합니다.

    Args:
        text: 분석할 메시지 텍스트
        sender_id: 발신자 ID (신뢰도 확인용)
        use_ai: True면 Kanana LLM 사용, False면 Rule-based

    Returns:
        AnalysisResult: 분석 결과
    """
    # Rule-based 분석
    detected_threats = detect_threat_keywords(text)
    detected_pii_requests = []

    # 개인정보 요구 패턴 검사
    if "개인정보요구" in detected_threats:
        detected_pii_requests.append("개인정보 요구 감지")

    risk_level = calculate_risk_level(0, len(detected_threats))

    reasons = []
    for threat_type in detected_threats:
        threat_descriptions = {
            "긴급송금": "긴급 송금 요청 패턴",
            "가족사칭": "가족 사칭 의심 패턴",
            "금융사기": "금융 사기 의심 패턴",
            "피싱링크": "의심스러운 링크 포함",
            "개인정보요구": "개인정보 요구 패턴",
        }
        reasons.append(threat_descriptions.get(threat_type, threat_type))

    # AI 분석 (옵션)
    if use_ai:
        instruct_model = LLMManager.get("instruct")
        if instruct_model:
            try:
                ai_result = instruct_model.analyze_text(text, analysis_type="threat")
                reasons.append(f"AI 분석: {ai_result[:200]}...")
            except Exception as e:
                reasons.append(f"AI 분석 실패: {str(e)}")

    # 권장 조치 결정
    if risk_level == RiskLevel.SAFE:
        recommended_action = "안전한 메시지입니다."
    elif risk_level == RiskLevel.LOW:
        recommended_action = "주의가 필요합니다. 발신자를 확인해주세요."
    elif risk_level == RiskLevel.MEDIUM:
        recommended_action = "의심스러운 메시지입니다. 송금이나 개인정보 제공을 자제해주세요."
    else:  # HIGH, CRITICAL
        recommended_action = "⚠️ 사기 의심 메시지입니다! 절대 응하지 마시고 신고해주세요."

    return AnalysisResult(
        risk_level=risk_level,
        reasons=reasons,
        recommended_action=recommended_action,
        is_secret_recommended=False,
    )


def analyze_image(image_path: str, use_ai: bool = False) -> AnalysisResult:
    """
    이미지 분석 - Vision OCR + PII 감지

    이미지에서 텍스트를 추출하고 개인정보를 분석합니다.

    처리 순서:
    1. Kanana Vision → 이미지에서 텍스트 추출 (OCR)
    2. 추출된 텍스트를 analyze_outgoing으로 분석

    Args:
        image_path: 이미지 파일 경로
        use_ai: True면 텍스트 분석에 Kanana Instruct 사용

    Returns:
        AnalysisResult: 분석 결과 (extracted_text 포함)
    """
    # 1. Vision 모델로 OCR
    vision_model = LLMManager.get("vision")
    if not vision_model:
        return AnalysisResult(
            risk_level=RiskLevel.SAFE,
            reasons=["Vision 모델을 사용할 수 없습니다."],
            recommended_action="이미지 분석을 수행할 수 없습니다.",
            is_secret_recommended=False,
        )

    try:
        extracted_text = vision_model.analyze_image(image_path)
    except Exception as e:
        return AnalysisResult(
            risk_level=RiskLevel.SAFE,
            reasons=[f"OCR 실패: {str(e)}"],
            recommended_action="이미지에서 텍스트를 추출할 수 없습니다.",
            is_secret_recommended=False,
        )

    # 2. 추출된 텍스트가 없거나 "텍스트 없음"인 경우
    if not extracted_text or "텍스트 없음" in extracted_text:
        return AnalysisResult(
            risk_level=RiskLevel.SAFE,
            reasons=["이미지에서 텍스트가 감지되지 않았습니다."],
            recommended_action="안전하게 전송 가능합니다.",
            is_secret_recommended=False,
            extracted_text=extracted_text,
        )

    # 3. 추출된 텍스트로 PII 분석
    result = analyze_outgoing(extracted_text, use_ai=use_ai)
    result.extracted_text = extracted_text

    return result
