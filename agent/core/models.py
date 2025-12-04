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
    # Agent B (수신 보호) 전용 필드
    category: Optional[str] = None  # MECE 카테고리 (A-1, B-2 등)
    category_name: Optional[str] = None  # 카테고리 이름 (가족 사칭 등)
    scam_probability: Optional[int] = None  # 사기 확률 (0-100%)
