"""
Core Data Models
KAT 에이전트 공통 데이터 모델 정의
"""
from pydantic import BaseModel
from enum import Enum
from typing import List, Optional


class RiskLevel(str, Enum):
    """위험도 레벨"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnalysisRequest(BaseModel):
    """분석 요청 모델"""
    text: str
    sender_id: Optional[str] = None
    receiver_id: Optional[str] = None


class AnalysisResponse(BaseModel):
    """분석 응답 모델"""
    risk_level: RiskLevel
    reasons: List[str]
    recommended_action: str
    is_secret_recommended: bool = False
