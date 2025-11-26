"""
Base Agent - Agent 공통 인터페이스
"""
from abc import ABC, abstractmethod
from ..core.models import AnalysisResponse


class BaseAgent(ABC):
    """모든 Agent의 기본 클래스"""

    @abstractmethod
    def analyze(self, text: str, **kwargs) -> AnalysisResponse:
        """
        메시지 분석 수행

        Args:
            text: 분석할 텍스트
            **kwargs: 추가 파라미터

        Returns:
            AnalysisResponse: 분석 결과
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent 이름"""
        pass
