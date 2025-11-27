"""
MCP Tools - FastMCP 기반 도구 정의
"""
from mcp.server.fastmcp import FastMCP
from ..core.models import RiskLevel, AnalysisResponse
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
