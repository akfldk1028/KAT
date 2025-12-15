"""
Score Utilities - 점수 계산 유틸리티 모듈

개선된 점수화 시스템을 위한 유틸리티 함수들:
- 시간대 위험도 조정
- 로그 스케일 신뢰도 계산
- 점수 정규화
"""
import math
from datetime import datetime
from typing import Optional


def time_risk_adjustment(timestamp: Optional[datetime] = None) -> int:
    """
    시간대 기반 위험도 조정

    Args:
        timestamp: 메시지 시간 (None이면 현재 시간 사용)

    Returns:
        위험도 조정 점수 (-5 ~ +15)

    로직:
    - 심야 (23시~6시): +15점 (사기 메시지 집중 시간)
    - 업무시간 (9시~18시): -5점 (정상 업무 메시지 가능성)
    - 기타: 0점
    """
    if timestamp is None:
        timestamp = datetime.now()

    hour = timestamp.hour

    # 심야 시간대 (23시 ~ 6시)
    if 23 <= hour or hour <= 6:
        return +15  # 사기 메시지 집중 시간

    # 업무 시간대 (9시 ~ 18시)
    elif 9 <= hour <= 18:
        return -5  # 정상 업무 메시지 가능성

    # 기타 시간 (6시~9시, 18시~23시)
    return 0


def calculate_logarithmic_trust_score(
    message_count: int,
    conversation_days: int
) -> int:
    """
    로그 스케일 기반 발신자 신뢰도 계산

    개선사항:
    - 기존 선형 계산 (message_count × 5)에서 로그 스케일로 변경
    - 초기 메시지에 대한 급격한 증가 방지
    - 장기 대화에 대한 충분한 보상

    Args:
        message_count: 발신자와 주고받은 총 메시지 수
        conversation_days: 대화 시작 후 경과 일수

    Returns:
        신뢰도 점수 (0~100)

    공식:
    - message_score = min(50, log₁.₅(message_count + 1) × 10)
    - days_score = min(50, log₁.₃(conversation_days + 1) × 15)
    - total = message_score + days_score

    예시:
    - 2개 메시지, 1일: 10 + 11 = 21
    - 10개 메시지, 7일: 34 + 35 = 69
    - 50개 메시지, 30일: 50 + 50 = 100
    """
    # 메시지 수 기반 신뢰도 (최대 50점)
    # log₁.₅(message_count + 1) × 10
    if message_count > 0:
        message_score = min(50, math.log(message_count + 1, 1.5) * 10)
    else:
        message_score = 0

    # 대화 기간 기반 신뢰도 (최대 50점)
    # log₁.₃(conversation_days + 1) × 15
    if conversation_days > 0:
        days_score = min(50, math.log(conversation_days + 1, 1.3) * 15)
    else:
        days_score = 0

    # 총 신뢰도 (0~100)
    total_trust = message_score + days_score

    return int(min(100, max(0, total_trust)))


def calculate_risk_adjustment_from_trust(
    trust_score: int,
    has_financial_request: bool = False
) -> int:
    """
    신뢰도 점수를 위험도 조정값으로 변환

    Args:
        trust_score: 신뢰도 점수 (0~100)
        has_financial_request: 금융 요청 포함 여부

    Returns:
        위험도 조정값 (-20 ~ +30)

    로직:
    - 높은 신뢰도 (70+): -20점 (위험도 감소)
    - 중간 신뢰도 (30-69): -10 ~ 0점
    - 낮은 신뢰도 (0-29): +10 ~ +20점 (위험도 증가)
    - 금융 요청 있으면 +10점 추가
    """
    # 신뢰도 기반 조정
    if trust_score >= 70:
        base_adjustment = -20  # 높은 신뢰도
    elif trust_score >= 50:
        base_adjustment = -10
    elif trust_score >= 30:
        base_adjustment = 0
    elif trust_score >= 10:
        base_adjustment = +10
    else:
        base_adjustment = +20  # 낮은 신뢰도

    # 금융 요청 시 추가 위험
    if has_financial_request:
        base_adjustment += 10

    return base_adjustment


def normalize_score_to_range(
    score: float,
    input_min: float,
    input_max: float,
    output_min: float = 0,
    output_max: float = 100
) -> int:
    """
    점수를 특정 범위로 정규화

    Args:
        score: 원본 점수
        input_min: 입력 범위 최소값
        input_max: 입력 범위 최대값
        output_min: 출력 범위 최소값
        output_max: 출력 범위 최대값

    Returns:
        정규화된 점수 (output_min ~ output_max)

    예시:
    normalize_score_to_range(120, 0, 150, 0, 100) → 80
    """
    if input_max == input_min:
        return output_min

    # 선형 정규화
    normalized = (score - input_min) / (input_max - input_min) * (output_max - output_min) + output_min

    # 범위 제한
    return int(min(output_max, max(output_min, normalized)))
