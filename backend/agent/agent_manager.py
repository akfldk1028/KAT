"""
Agent Manager - 서브에이전트 관리
"""

from typing import Optional
from .mcp.tools import analyze_outgoing, analyze_incoming, analyze_image
from .core.models import AnalysisResult


class OutgoingAgent:
    """안심 전송 에이전트 (발신 메시지 분석)"""

    def analyze(self, text: str, use_ai: bool = False) -> AnalysisResult:
        return analyze_outgoing(text, use_ai=use_ai)


class IncomingAgent:
    """안심 가드 에이전트 (수신 메시지 분석)"""

    def analyze(self, text: str, sender_id: Optional[str] = None, use_ai: bool = False) -> AnalysisResult:
        return analyze_incoming(text, sender_id=sender_id, use_ai=use_ai)


class ImageAgent:
    """이미지 분석 에이전트 (OCR + PII 감지)"""

    def analyze(self, image_path: str, use_ai: bool = False) -> AnalysisResult:
        return analyze_image(image_path, use_ai=use_ai)


class AgentManager:
    """에이전트 매니저 - 싱글톤 패턴으로 에이전트 인스턴스 관리"""

    _outgoing: Optional[OutgoingAgent] = None
    _incoming: Optional[IncomingAgent] = None
    _image: Optional[ImageAgent] = None

    @classmethod
    def get_outgoing(cls) -> OutgoingAgent:
        if cls._outgoing is None:
            cls._outgoing = OutgoingAgent()
        return cls._outgoing

    @classmethod
    def get_incoming(cls) -> IncomingAgent:
        if cls._incoming is None:
            cls._incoming = IncomingAgent()
        return cls._incoming

    @classmethod
    def get_image(cls) -> ImageAgent:
        if cls._image is None:
            cls._image = ImageAgent()
        return cls._image
