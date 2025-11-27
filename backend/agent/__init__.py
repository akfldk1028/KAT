# DualGuard Agent Package

from .mcp.tools import analyze_outgoing, analyze_incoming, analyze_image
from .core.models import RiskLevel, AnalysisResult

# Legacy compatibility - AnalysisRequest/Response for routers
from pydantic import BaseModel
from typing import Optional, List


class AnalysisRequest(BaseModel):
    text: str
    sender_id: Optional[str] = None


class AnalysisResponse(BaseModel):
    risk_level: str
    reasons: List[str]
    recommended_action: str
    is_secret_recommended: bool = False
    detected_pii: List[str] = []
    extracted_text: Optional[str] = None


__all__ = [
    "analyze_outgoing",
    "analyze_incoming",
    "analyze_image",
    "RiskLevel",
    "AnalysisResult",
    "AnalysisRequest",
    "AnalysisResponse",
]
