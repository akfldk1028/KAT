"""
MCP Tools - FastMCP 기반 도구 정의
AI가 호출할 수 있는 모든 분석 도구를 제공
"""
from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Any
from ..core.models import RiskLevel, AnalysisResponse
from ..core.pattern_matcher import (
    get_pii_patterns,
    get_document_types,
    get_combination_rules,
    detect_pii,
    detect_document_type,
    calculate_risk,
    get_risk_action
)
from ..agents.outgoing import OutgoingAgent
from ..agents.incoming import IncomingAgent

from ..llm.kanana import LLMManager

# MCP 서버 인스턴스
mcp = FastMCP("DualGuard")

# Agent 인스턴스 (Lazy Singleton)
_outgoing_agent = None
_incoming_agent = None


def _get_outgoing_agent() -> OutgoingAgent:
    global _outgoing_agent
    if _outgoing_agent is None:
        _outgoing_agent = OutgoingAgent()
    return _outgoing_agent


def _get_incoming_agent() -> IncomingAgent:
    global _incoming_agent
    if _incoming_agent is None:
        _incoming_agent = IncomingAgent()
    return _incoming_agent


@mcp.tool()
def analyze_outgoing(text: str, use_ai: bool = False) -> AnalysisResponse:
    """
    Analyze outgoing message for sensitive information.
    발신 메시지의 민감정보(계좌번호, 주민번호 등)를 감지합니다.

    Args:
        text: 분석할 메시지 내용
        use_ai: Kanana LLM 사용 여부 (기본: False = rule-based 분석)
                True로 설정하면 Kanana Instruct 모델이 ReAct 패턴으로 분석

    Returns:
        AnalysisResponse: 위험도, 감지 이유, 권장 조치
    """
    agent = _get_outgoing_agent()
    return agent.analyze(text, use_ai=use_ai)


@mcp.tool()
def analyze_incoming(text: str, sender_id: str = None, use_ai: bool = False) -> AnalysisResponse:
    """
    Analyze incoming message for phishing or scams.
    수신 메시지의 피싱/사기 위협을 탐지합니다.

    Args:
        text: 분석할 메시지 내용
        sender_id: 발신자 ID (선택)
        use_ai: Kanana Safeguard AI 사용 여부 (기본: False)

    Returns:
        AnalysisResponse: 위험도, 감지 이유, 권장 조치
    """
    agent = _get_incoming_agent()
    return agent.analyze(text, sender_id=sender_id, use_ai=use_ai)


@mcp.tool()
def analyze_image(image_path: str, use_ai: bool = True) -> AnalysisResponse:
    """
    Analyze text within an image using Kanana Vision Model.
    이미지 내 텍스트를 추출하여 민감정보를 분석합니다.

    순차 처리 (GPU 메모리 효율화):
    1. Kanana Vision (3B) → 이미지에서 텍스트 추출 (OCR)
    2. Vision 언로드 → GPU 메모리 해제
    3. 추출된 텍스트 → 2-Tier 분석 (빠른 필터링 → LLM 정밀 분석)

    Args:
        image_path: 이미지 파일 경로
        use_ai: 텍스트 분석에 Kanana Instruct 사용 여부 (기본: True)
                2-Tier 방식으로 의심 메시지에만 LLM 호출됨

    Returns:
        AnalysisResponse: 위험도, 감지 이유, 권장 조치
    """
    try:
        # Step 1: Vision 모델로 OCR
        print("[analyze_image] Step 1: Loading Vision model for OCR...")
        vision_model = LLMManager.get("vision")
        if not vision_model:
            return AnalysisResponse(
                risk_level=RiskLevel.LOW,
                reasons=["Vision Model loading failed"],
                recommended_action="시스템 관리자에게 문의하세요",
                is_secret_recommended=False
            )

        # Extract text using Kanana Vision
        extracted_text = vision_model.analyze_image(image_path)
        print(f"[analyze_image] OCR Result: {extracted_text[:200]}..." if len(extracted_text) > 200 else f"[analyze_image] OCR Result: {extracted_text}")

        # Step 2: 텍스트 분석 (2-Tier 방식)
        # - Tier 1: 빠른 필터링 (숫자/키워드 패턴 체크)
        # - Tier 2: 의심 메시지만 LLM 정밀 분석
        # LLMManager.sequential_mode=True이므로 Instruct 로드 시 Vision 자동 언로드
        print(f"[analyze_image] Step 2: Analyzing extracted text (use_ai={use_ai})...")
        return analyze_outgoing(extracted_text, use_ai=use_ai)

    except Exception as e:
        return AnalysisResponse(
            risk_level=RiskLevel.LOW,
            reasons=[f"이미지 분석 중 오류 발생: {str(e)}"],
            recommended_action="분석 실패",
            is_secret_recommended=False
        )


# ============================================================
# Pattern Matcher MCP Tools - AI가 직접 호출하는 분석 도구
# ============================================================

@mcp.tool()
def list_pii_patterns() -> Dict[str, Any]:
    """
    List all PII patterns that can be detected.
    감지 가능한 모든 개인정보(PII) 패턴 목록을 반환합니다.

    AI가 어떤 종류의 민감정보를 감지할 수 있는지 파악하는 데 사용합니다.

    Returns:
        카테고리별 PII 패턴 정보 (id, name_ko, risk_level, requires_ai)
    """
    return get_pii_patterns()


@mcp.tool()
def list_document_types() -> List[Dict]:
    """
    List all document types for image detection.
    이미지에서 감지 가능한 문서 유형 목록을 반환합니다.

    Vision OCR로 추출한 텍스트에서 서류 종류를 식별하는 데 사용합니다.
    (예: 주민등록증, 여권, 운전면허증 등)

    Returns:
        문서 유형 목록 (id, name_ko, risk_level, keywords)
    """
    return get_document_types()


@mcp.tool()
def get_risk_rules() -> Dict[str, Any]:
    """
    Get combination rules and auto-escalation rules.
    위험도 조합 규칙과 자동 상향 규칙을 반환합니다.

    여러 민감정보가 함께 있을 때 위험도가 어떻게 상향되는지 파악하는 데 사용합니다.
    (예: 이름+주민번호 조합 → CRITICAL)

    Returns:
        combination_rules: 조합 규칙
        auto_escalation: 자동 상향 규칙 (개수 기반, 카테고리 조합)
    """
    return get_combination_rules()


@mcp.tool()
def scan_pii(text: str) -> Dict[str, Any]:
    """
    Scan text for PII using regex patterns.
    정규식 패턴으로 텍스트에서 개인정보(PII)를 스캔합니다.

    빠른 1차 필터링에 사용합니다. requires_ai=true 항목은 별도 AI 분석 필요.

    Args:
        text: 분석할 텍스트

    Returns:
        found_pii: 감지된 PII 목록 [{id, category, value, risk_level, name_ko}]
        categories_found: 감지된 카테고리 목록
        highest_risk: 가장 높은 위험도
        count: 감지된 PII 개수
    """
    return detect_pii(text)


@mcp.tool()
def identify_document(ocr_text: str) -> Dict[str, Any]:
    """
    Identify document type from OCR text.
    OCR로 추출한 텍스트에서 문서 유형을 식별합니다.

    Vision 모델이 추출한 텍스트를 입력받아 어떤 종류의 서류인지 판별합니다.

    Args:
        ocr_text: OCR로 추출한 텍스트

    Returns:
        document_type: 문서 유형 ID (예: "resident_card")
        name_ko: 문서 유형 한글명 (예: "주민등록증")
        risk_level: 해당 문서의 기본 위험도
        confidence: 매칭 신뢰도 (high/medium/low/none)
        matched_keywords: 매칭된 키워드 수
    """
    return detect_document_type(ocr_text)


@mcp.tool()
def evaluate_risk(detected_items: List[Dict]) -> Dict[str, Any]:
    """
    Evaluate final risk level based on detected items.
    감지된 항목들의 최종 위험도를 평가합니다.

    조합 규칙(combination_rules)과 자동 상향 규칙(auto_escalation)을 적용하여
    개별 항목보다 높은 위험도가 적용될 수 있습니다.

    Args:
        detected_items: scan_pii()에서 반환된 found_pii 목록

    Returns:
        final_risk: 최종 위험도 (조합 규칙 적용 후)
        base_risk: 기본 위험도 (가장 높은 개별 항목)
        escalation_reason: 위험도 상향 이유 (해당 시)
        is_secret_recommended: 시크릿 전송 권장 여부
        matched_rules: 매칭된 조합 규칙 ID 목록
        detected_count: 감지된 항목 수
    """
    return calculate_risk(detected_items)


@mcp.tool()
def get_action_for_risk(risk_level: str) -> str:
    """
    Get recommended action for a given risk level.
    위험도에 따른 권장 조치를 반환합니다.

    Args:
        risk_level: 위험도 (LOW, MEDIUM, HIGH, CRITICAL)

    Returns:
        권장 조치 문자열 (예: "시크릿 전송 필수")
    """
    return get_risk_action(risk_level)


@mcp.tool()
def analyze_full(text: str) -> Dict[str, Any]:
    """
    Full analysis pipeline: scan PII + evaluate risk + get action.
    전체 분석 파이프라인: PII 스캔 → 위험도 평가 → 권장 조치.

    단일 호출로 전체 분석을 수행합니다.

    Args:
        text: 분석할 텍스트

    Returns:
        pii_scan: PII 스캔 결과
        risk_evaluation: 위험도 평가 결과
        recommended_action: 권장 조치
        summary: 분석 요약 (한글)
    """
    # 1. PII 스캔
    pii_result = detect_pii(text)

    # 2. 위험도 평가
    risk_result = calculate_risk(pii_result["found_pii"])

    # 3. 권장 조치
    action = get_risk_action(risk_result["final_risk"])

    # 4. 요약 생성
    if pii_result["count"] == 0:
        summary = "민감정보가 감지되지 않았습니다."
    else:
        detected_names = [item["name_ko"] for item in pii_result["found_pii"]]
        unique_names = list(set(detected_names))
        summary = f"{len(unique_names)}종의 민감정보 감지: {', '.join(unique_names)}. {action}"

    return {
        "pii_scan": pii_result,
        "risk_evaluation": risk_result,
        "recommended_action": action,
        "summary": summary
    }
