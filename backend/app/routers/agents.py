"""
Kanana DualGuard Agent API Router
서브에이전트(Outgoing, Incoming)를 호출하는 REST API 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
from pathlib import Path

# agent 모듈 경로 추가
agent_path = Path(__file__).parent.parent.parent.parent / "agent"
sys.path.insert(0, str(agent_path))

from agent.agent_manager import AgentManager
from agent import RiskLevel

router = APIRouter()

# ===== Request/Response 모델 =====

class ConversationMessage(BaseModel):
    """대화 히스토리 메시지"""
    sender_id: Optional[int] = None
    message: str
    timestamp: Optional[str] = None


class MessageAnalysisRequest(BaseModel):
    """메시지 분석 요청"""
    text: str
    sender_id: Optional[str] = None
    receiver_id: Optional[str] = None
    conversation_history: Optional[List[ConversationMessage]] = None
    use_ai: bool = True


# === [수정] MECE 카테고리 필드 추가 ===
# Incoming Agent의 Stage 1 분류 결과를 클라이언트에 전달
class MessageAnalysisResponse(BaseModel):
    """메시지 분석 응답"""
    risk_level: str
    reasons: List[str]
    recommended_action: str
    is_secret_recommended: bool = False
    # MECE 카테고리 정보 (Incoming Agent 전용)
    category: Optional[str] = None  # "A-1", "B-2", "C-3" 등
    category_name: Optional[str] = None  # "가족 사칭 (액정 파손)" 등
    scam_probability: Optional[int] = None  # 0-100
# === [수정 끝] ===


# ===== 서브에이전트는 AgentManager를 통해 관리 =====
# Lazy loading으로 필요할 때만 인스턴스 생성


# ===== API 엔드포인트 =====

@router.post("/analyze/outgoing", response_model=MessageAnalysisResponse)
async def analyze_outgoing_message(request: MessageAnalysisRequest):
    """
    안심 전송 Agent (Outgoing) - 발신 메시지 분석

    민감정보(계좌번호, 주민번호, 카드번호 등)를 감지하고
    시크릿 전송 추천 여부를 판단합니다.

    Args:
        request: 메시지 분석 요청 (text, sender_id, receiver_id)

    Returns:
        분석 결과 (위험도, 이유, 권장 조치, 시크릿 전송 추천 여부)
    """
    try:
        # AgentManager를 통해 Outgoing Agent 가져오기
        outgoing_agent = AgentManager.get_outgoing()
        result = outgoing_agent.analyze(request.text)

        return MessageAnalysisResponse(
            risk_level=result.risk_level.value,
            reasons=result.reasons,
            recommended_action=result.recommended_action,
            is_secret_recommended=result.is_secret_recommended
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Outgoing analysis failed: {str(e)}")


@router.post("/analyze/incoming", response_model=MessageAnalysisResponse)
async def analyze_incoming_message(request: MessageAnalysisRequest):
    """
    안심 가드 Agent (Incoming) - 수신 메시지 분석

    피싱, 사기, 가족 사칭 등의 위험한 메시지를 감지하고
    위험도에 따른 조치를 제안합니다.

    v9.0.1: 대화 맥락 기반 멀티메시지 사기 감지 지원
    - conversation_history로 이전 대화 히스토리를 받아 전체 맥락 분석
    - 개별 메시지는 무해해 보여도 전체 흐름이 사기 패턴이면 감지

    Args:
        request: 메시지 분석 요청 (text, sender_id, receiver_id, conversation_history)

    Returns:
        분석 결과 (위험도, 이유, 권장 조치, 카테고리)
    """
    try:
        # AgentManager를 통해 Incoming Agent 가져오기
        incoming_agent = AgentManager.get_incoming()

        # 대화 맥락을 dict 리스트로 변환
        history_list = None
        if request.conversation_history:
            history_list = [
                {
                    "sender_id": msg.sender_id,
                    "message": msg.message,
                    "timestamp": msg.timestamp
                }
                for msg in request.conversation_history
            ]
            print(f"[API] Incoming 분석: text={request.text[:30]}..., history_count={len(history_list)}")

        result = incoming_agent.analyze(
            text=request.text,
            sender_id=request.sender_id,
            user_id=request.receiver_id,
            conversation_history=history_list,
            use_ai=request.use_ai
        )

        # === [수정] MECE 카테고리 정보 포함 ===
        return MessageAnalysisResponse(
            risk_level=result.risk_level.value,
            reasons=result.reasons,
            recommended_action=result.recommended_action,
            is_secret_recommended=False,
            # MECE 카테고리 정보 (있으면 전달)
            category=getattr(result, 'category', None),
            category_name=getattr(result, 'category_name', None),
            scam_probability=getattr(result, 'scam_probability', None)
        )
        # === [수정 끝] ===
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Incoming analysis failed: {str(e)}")


@router.get("/health")
async def health_check():
    """
    서브에이전트 헬스체크

    Returns:
        상태 정보
    """
    return {
        "status": "healthy",
        "agents": {
            "outgoing": "ready",
            "incoming": "ready"
        },
        "message": "Kanana DualGuard Agents are operational"
    }
