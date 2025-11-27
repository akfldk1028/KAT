"""
Core models for DualGuard Agent
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


class RiskLevel(Enum):
    """위험 수준"""
    SAFE = "safe"           # 안전
    LOW = "low"             # 낮은 위험
    MEDIUM = "medium"       # 중간 위험
    HIGH = "high"           # 높은 위험
    CRITICAL = "critical"   # 심각한 위험


@dataclass
class AnalysisResult:
    """분석 결과"""
    risk_level: RiskLevel
    reasons: List[str] = field(default_factory=list)
    recommended_action: str = ""
    is_secret_recommended: bool = False  # 비밀 채팅 권장 여부
    detected_pii: List[str] = field(default_factory=list)  # 감지된 개인정보 종류
    extracted_text: Optional[str] = None  # OCR로 추출된 텍스트 (이미지 분석 시)


@dataclass
class PIIPattern:
    """개인정보 패턴 정의"""
    name: str           # 패턴 이름 (예: "주민등록번호")
    pattern: str        # 정규식 패턴
    risk_level: RiskLevel
    description: str    # 설명


@dataclass
class ThreatPattern:
    """위협 패턴 정의 (피싱/사기)"""
    name: str           # 패턴 이름
    keywords: List[str] # 키워드 목록
    risk_level: RiskLevel
    description: str
