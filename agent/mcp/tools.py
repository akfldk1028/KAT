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
def analyze_outgoing(text: str) -> AnalysisResponse:
    """
    Analyze outgoing message for sensitive information.
    발신 메시지의 민감정보(계좌번호, 주민번호 등)를 감지합니다.

    Args:
        text: 분석할 메시지 내용

    Returns:
        AnalysisResponse: 위험도, 감지 이유, 권장 조치
    """
    agent = _get_outgoing_agent()
    return agent.analyze(text)


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
def analyze_image(image_path: str) -> AnalysisResponse:
    """
    Analyze text within an image using Kanana Vision Model.
    이미지 내 텍스트를 추출하여 민감정보를 분석합니다.

    Args:
        image_path: 이미지 파일 경로

    Returns:
        AnalysisResponse: 위험도, 감지 이유, 권장 조치
    """
    try:
        # Get Vision Model
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
        
        # Analyze extracted text using Outgoing Agent (PII detection)
        return analyze_outgoing(extracted_text)
        
    except Exception as e:
        return AnalysisResponse(
            risk_level=RiskLevel.LOW,
            reasons=[f"이미지 분석 중 오류 발생: {str(e)}"],
            recommended_action="분석 실패",
            is_secret_recommended=False
        )
