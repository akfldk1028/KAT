"""
KAT Agent Package
카카오톡 양방향 보안 에이전트

Package Structure:
- core/: 핵심 데이터 모델
- agents/: Agent 구현 (OutgoingAgent, IncomingAgent)
- mcp/: MCP 도구 및 서버
- llm/: Kanana LLM 관리
- tests/: 단위 테스트
"""

# Core models
from .core.models import RiskLevel, AnalysisRequest, AnalysisResponse

# Agents
from .agents.outgoing import OutgoingAgent
from .agents.incoming import IncomingAgent

# MCP tools
from .mcp.tools import analyze_outgoing, analyze_incoming, analyze_image

__all__ = [
    # Models
    "RiskLevel",
    "AnalysisRequest",
    "AnalysisResponse",
    # Agents
    "OutgoingAgent",
    "IncomingAgent",
    # MCP Tools
    "analyze_outgoing",
    "analyze_incoming",
    "analyze_image",
]

__version__ = "0.1.0"
