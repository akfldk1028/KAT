"""
Conversation Analyzer - 대화관계 분석 모듈
발신자와의 대화 이력을 분석하여 신뢰도 판단

기능:
- 대화 이력 조회 (첫 메시지인지 확인)
- 발신자 신뢰도 계산
- 대화 패턴 분석 (갑작스러운 송금 요청 등)
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


# Mock 대화 이력 DB (실제로는 채팅 서버 DB 연동)
_conversation_history: Dict[str, Dict] = {}


def register_conversation(user_id: int, sender_id: int, message: str, timestamp: datetime = None):
    """
    대화 이력 등록 (테스트/시뮬레이션용)
    실제 운영에서는 채팅 서버 DB에서 자동으로 관리됨
    """
    if timestamp is None:
        timestamp = datetime.now()

    key = f"{user_id}_{sender_id}"
    if key not in _conversation_history:
        _conversation_history[key] = {
            "user_id": user_id,
            "sender_id": sender_id,
            "first_contact": timestamp,
            "last_contact": timestamp,
            "message_count": 0,
            "messages": []
        }

    _conversation_history[key]["last_contact"] = timestamp
    _conversation_history[key]["message_count"] += 1
    _conversation_history[key]["messages"].append({
        "content": message[:100],  # 앞 100자만 저장
        "timestamp": timestamp.isoformat()
    })


def get_conversation_history(user_id: int, sender_id: int) -> Dict[str, Any]:
    """
    발신자와의 대화 이력 조회

    Args:
        user_id: 수신자 (현재 사용자) ID
        sender_id: 발신자 ID

    Returns:
        has_history: 이전 대화 이력 존재 여부
        is_first_message: 첫 메시지 여부
        conversation_days: 대화한 기간 (일)
        message_count: 총 메시지 수
        trust_score: 신뢰도 점수 (0-100)
        trust_level: 신뢰 레벨 (unknown/low/medium/high)
    """
    key = f"{user_id}_{sender_id}"
    history = _conversation_history.get(key)

    if history is None:
        return {
            "has_history": False,
            "is_first_message": True,
            "conversation_days": 0,
            "message_count": 0,
            "trust_score": 0,
            "trust_level": "unknown",
            "first_contact": None,
            "last_contact": None
        }

    # 대화 기간 계산
    first_contact = datetime.fromisoformat(history["first_contact"]) if isinstance(history["first_contact"], str) else history["first_contact"]
    last_contact = datetime.fromisoformat(history["last_contact"]) if isinstance(history["last_contact"], str) else history["last_contact"]
    conversation_days = (last_contact - first_contact).days

    # 신뢰도 계산
    trust_score = calculate_trust_score(
        message_count=history["message_count"],
        conversation_days=conversation_days
    )

    trust_level = get_trust_level(trust_score)

    return {
        "has_history": True,
        "is_first_message": history["message_count"] == 1,
        "conversation_days": conversation_days,
        "message_count": history["message_count"],
        "trust_score": trust_score,
        "trust_level": trust_level,
        "first_contact": first_contact.isoformat() if first_contact else None,
        "last_contact": last_contact.isoformat() if last_contact else None
    }


def calculate_trust_score(message_count: int, conversation_days: int) -> int:
    """
    신뢰도 점수 계산

    기준:
    - 메시지 수: 많을수록 신뢰도 상승
    - 대화 기간: 길수록 신뢰도 상승
    - 최대 100점
    """
    # 메시지 수 기반 점수 (최대 50점)
    message_score = min(50, message_count * 5)

    # 대화 기간 기반 점수 (최대 50점)
    days_score = min(50, conversation_days * 2)

    return message_score + days_score


def get_trust_level(trust_score: int) -> str:
    """신뢰도 점수 → 레벨 변환"""
    if trust_score >= 70:
        return "high"
    elif trust_score >= 40:
        return "medium"
    elif trust_score > 0:
        return "low"
    else:
        return "unknown"


def analyze_sender_risk(user_id: int, sender_id: int, current_message: str) -> Dict[str, Any]:
    """
    발신자 위험도 종합 분석

    대화 이력 + 현재 메시지 패턴을 종합하여 위험도 판단

    Args:
        user_id: 수신자 ID
        sender_id: 발신자 ID
        current_message: 현재 수신 메시지

    Returns:
        sender_trust: 발신자 신뢰 정보
        risk_factors: 위험 요소 목록
        risk_adjustment: 위험도 조정값 (-50 ~ +50)
        warning_message: 경고 메시지 (있는 경우)
    """
    # 대화 이력 조회
    history = get_conversation_history(user_id, sender_id)

    risk_factors = []
    risk_adjustment = 0
    warning_message = None

    # 1. 첫 메시지 위험도
    if history["is_first_message"]:
        risk_factors.append({
            "factor": "first_message",
            "description": "처음 받는 메시지입니다",
            "adjustment": 20
        })
        risk_adjustment += 20
        warning_message = "처음 연락하는 발신자입니다. 주의가 필요합니다."

    # 2. 낮은 신뢰도 발신자
    elif history["trust_level"] == "low":
        risk_factors.append({
            "factor": "low_trust",
            "description": "대화 이력이 적은 발신자입니다",
            "adjustment": 10
        })
        risk_adjustment += 10

    # 3. 높은 신뢰도 발신자 (위험도 감소)
    elif history["trust_level"] == "high":
        risk_factors.append({
            "factor": "high_trust",
            "description": "오랫동안 대화한 신뢰할 수 있는 발신자입니다",
            "adjustment": -20
        })
        risk_adjustment -= 20

    # 4. 갑작스러운 금융 요청 패턴 감지
    financial_keywords = ["송금", "이체", "계좌", "돈", "급하게", "빨리", "입금"]
    has_financial_request = any(kw in current_message for kw in financial_keywords)

    if has_financial_request and history["trust_level"] in ["unknown", "low"]:
        risk_factors.append({
            "factor": "sudden_financial_request",
            "description": "신뢰도가 낮은 발신자의 금융 관련 요청",
            "adjustment": 30
        })
        risk_adjustment += 30
        warning_message = "신뢰도가 낮은 발신자가 금융 관련 요청을 하고 있습니다!"

    return {
        "sender_trust": history,
        "risk_factors": risk_factors,
        "risk_adjustment": risk_adjustment,
        "warning_message": warning_message
    }


def clear_conversation_history():
    """대화 이력 초기화 (테스트용)"""
    global _conversation_history
    _conversation_history = {}


def seed_test_data():
    """테스트용 대화 이력 시드 데이터 생성"""
    # 신뢰할 수 있는 친구 (오래된 대화 이력)
    base_time = datetime.now() - timedelta(days=365)
    for i in range(100):
        register_conversation(
            user_id=1,
            sender_id=2,  # test123 → test1234
            message=f"테스트 메시지 {i}",
            timestamp=base_time + timedelta(days=i * 3)
        )

    # 새로운 발신자 (대화 이력 없음) - sender_id=99는 이력 없음
