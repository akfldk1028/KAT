"""
FastAPI Agent API Server
MCP 도구를 HTTP 엔드포인트로 노출

포트: 8002
엔드포인트:
- POST /api/agents/analyze/outgoing - 발신 메시지 분석
- POST /api/agents/analyze/incoming - 수신 메시지 분석
- POST /api/agents/analyze/image - 이미지 분석 (Vision OCR + PII 감지)
- POST /api/secret/create - 시크릿 메시지 생성
- GET /api/secret/view/{secret_id} - 시크릿 메시지 열람
- GET /api/agents/health - 헬스체크
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가 (루트의 agent/ 모듈 우선 사용)
PROJECT_ROOT = Path(__file__).parent.parent.parent
# backend/agent/ 대신 루트의 agent/를 사용하도록 경로 우선순위 설정
sys.path.insert(0, str(PROJECT_ROOT))
# backend/ 경로 제거 (있으면) - 루트 agent 우선
backend_path = str(Path(__file__).parent.parent)
if backend_path in sys.path:
    sys.path.remove(backend_path)

# === Prometheus 메트릭 모듈 로드 ===
METRICS_ENABLED = False
kat_metrics = None
setup_metrics = None
try:
    sys.path.insert(0, str(PROJECT_ROOT / "ops" / "monitoring"))
    from metrics import setup_metrics, kat_metrics
    METRICS_ENABLED = True
    print("[Metrics] 메트릭 모듈 로드 성공")
except ImportError as e:
    print(f"[Metrics] 메트릭 모듈 로드 실패 (무시됨): {e}")

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import tempfile
import shutil
from datetime import datetime, timedelta
import uuid

# SQLAlchemy for Secret Messages
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# MCP 도구 임포트 (v3.1 - category 필드 포함)
from agent.mcp.tools import analyze_outgoing, analyze_incoming, analyze_image, mcp
from agent.core.models import RiskLevel

# === Database Setup ===
DATABASE_PATH = PROJECT_ROOT / "kanana_dualguard.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class SecretMessageModel(Base):
    """시크릿 메시지 DB 모델"""
    __tablename__ = "secret_messages"

    id = Column(Integer, primary_key=True, index=True)
    secret_id = Column(String, unique=True, index=True)
    room_id = Column(Integer, index=True)
    sender_id = Column(Integer, index=True)
    original_message = Column(Text)
    message_type = Column(String, default="text")
    image_url = Column(String, nullable=True)
    expiry_seconds = Column(Integer, default=60)
    require_auth = Column(Boolean, default=False)
    prevent_capture = Column(Boolean, default=True)
    is_viewed = Column(Boolean, default=False)
    viewed_at = Column(DateTime, nullable=True)
    is_expired = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)


# Create tables
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(
    title="DualGuard Agent API",
    description="카카오톡 양방향 보안 에이전트 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Prometheus 메트릭 설정 ===
if METRICS_ENABLED and setup_metrics:
    setup_metrics(app)
    print("[Metrics] Prometheus /metrics 엔드포인트 활성화")

# MCP 서버를 FastAPI에 마운트 (SSE 방식)
# /mcp 경로에서 MCP 프로토콜 지원
try:
    mcp_app = mcp.sse_app()
    app.mount("/mcp", mcp_app)
    print("[MCP] SSE 서버가 /mcp 경로에 마운트됨")
except Exception as e:
    print(f"[MCP] SSE 마운트 실패: {e}, HTTP 방식 시도...")
    try:
        # HTTP 방식 폴백
        mcp_http = mcp.http_app()
        app.mount("/mcp", mcp_http)
        print("[MCP] HTTP 서버가 /mcp 경로에 마운트됨")
    except Exception as e2:
        print(f"[MCP] HTTP 마운트도 실패: {e2}")


# === Request/Response 모델 ===

class OutgoingRequest(BaseModel):
    text: str
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    use_ai: bool = True  # Kanana LLM 사용 (테스트용 기본값 True)


class ConversationMessage(BaseModel):
    """대화 히스토리 메시지"""
    sender_id: int
    message: str
    timestamp: Optional[str] = None


class IncomingRequest(BaseModel):
    text: str
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    conversation_history: Optional[List[ConversationMessage]] = None  # 대화 맥락
    use_ai: bool = True  # Kanana LLM 사용 (테스트용 기본값 True)


class AnalysisResponse(BaseModel):
    risk_level: str
    reasons: List[str]
    recommended_action: str
    is_secret_recommended: bool
    # Agent B (수신 보호) 전용 필드
    category: Optional[str] = None  # MECE 카테고리 (A-1, B-2 등)
    category_name: Optional[str] = None  # 카테고리 이름 (가족 사칭 등)
    scam_probability: Optional[int] = None  # 사기 확률 (0-100%)


# === 엔드포인트 ===

@app.get("/api/agents/health")
async def health_check():
    """헬스체크"""
    return {"status": "ok", "service": "DualGuard Agent API"}


@app.get("/api/mcp/health")
async def mcp_health_check():
    """
    MCP 서버 헬스체크 - 실제 동작 상태 확인

    Returns:
        status: healthy/degraded/unhealthy
        mcp_server: MCP 서버 인스턴스 상태
        tools_registered: 등록된 도구 수
        tools_list: 실제 등록된 도구 목록
        test_call: 간단한 도구 호출 테스트 결과
    """
    import time
    start_time = time.time()

    health_result = {
        "status": "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }

    try:
        # 1. MCP 서버 인스턴스 확인
        if mcp is None:
            health_result["checks"]["mcp_instance"] = {"status": "fail", "message": "MCP 인스턴스 없음"}
        else:
            health_result["checks"]["mcp_instance"] = {"status": "pass", "name": mcp.name}

        # 2. 등록된 도구 목록 확인 (실제 list_tools 호출)
        try:
            # FastMCP의 _tool_manager에서 도구 목록 가져오기
            tools = list(mcp._tool_manager._tools.keys()) if hasattr(mcp, '_tool_manager') else []
            health_result["checks"]["tools_registered"] = {
                "status": "pass" if len(tools) > 0 else "warn",
                "count": len(tools),
                "tools": tools[:10]  # 처음 10개만
            }
        except Exception as e:
            health_result["checks"]["tools_registered"] = {"status": "fail", "error": str(e)}

        # 3. 간단한 도구 호출 테스트 (analyze_outgoing with safe text)
        try:
            test_result = analyze_outgoing("테스트 메시지", use_ai=False)
            health_result["checks"]["tool_test"] = {
                "status": "pass",
                "tool": "analyze_outgoing",
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            health_result["checks"]["tool_test"] = {"status": "fail", "error": str(e)}

        # 4. 최종 상태 결정
        checks = health_result["checks"]
        if all(c.get("status") == "pass" for c in checks.values()):
            health_result["status"] = "healthy"
        elif any(c.get("status") == "fail" for c in checks.values()):
            health_result["status"] = "unhealthy"
        else:
            health_result["status"] = "degraded"

        # 5. 메트릭 기록 (MCP 서버 상태)
        if METRICS_ENABLED and kat_metrics:
            is_healthy = health_result["status"] == "healthy"
            tools_count = health_result["checks"].get("tools_registered", {}).get("count", 0)
            duration = time.time() - start_time

            kat_metrics.record_mcp_server_status(is_healthy, tools_count)
            kat_metrics.record_mcp_health_check(duration)

        health_result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return health_result

    except Exception as e:
        health_result["status"] = "unhealthy"
        health_result["error"] = str(e)
        return health_result


@app.get("/api/mcp/info")
async def mcp_info():
    """MCP 서버 정보"""
    return {
        "status": "active",
        "name": mcp.name,
        "endpoint": "/mcp",
        "transport": "SSE",
        "tools": [
            "analyze_outgoing",
            "analyze_incoming",
            "analyze_image",
            "scan_pii",
            "evaluate_risk",
            "analyze_full",
            "list_pii_patterns",
            "list_document_types",
            "get_risk_rules",
            "identify_document",
            "get_action_for_risk"
        ],
        "description": "DualGuard MCP 서버 - 카카오톡 양방향 보안 분석"
    }


@app.post("/api/agents/analyze/outgoing", response_model=AnalysisResponse)
async def api_analyze_outgoing(request: OutgoingRequest):
    """
    안심 전송 Agent - 발신 메시지 분석
    민감정보(계좌번호, 주민번호 등)를 감지합니다.

    use_ai=True: Kanana LLM이 ReAct 패턴으로 분석
    use_ai=False: Rule-based 패턴 매칭 (기본값)
    """
    try:
        result = analyze_outgoing(request.text, use_ai=request.use_ai)

        # 메트릭 기록 (Agent A)
        if METRICS_ENABLED and kat_metrics:
            kat_metrics.record_agent_a_detection(
                risk_level=result.risk_level.value,
                pii_type=result.reasons[0] if result.reasons else "unknown"
            )
            if result.risk_level.value in ["HIGH", "CRITICAL"]:
                kat_metrics.record_agent_a_blocked(result.risk_level.value)

        return AnalysisResponse(
            risk_level=result.risk_level.value,
            reasons=result.reasons,
            recommended_action=result.recommended_action,
            is_secret_recommended=result.is_secret_recommended
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/analyze/incoming", response_model=AnalysisResponse)
async def api_analyze_incoming(request: IncomingRequest):
    """
    안심 가드 Agent - 수신 메시지 분석
    피싱, 사기, 가족 사칭 등을 감지합니다.

    v2.0: 대화 히스토리 기반 맥락 분석 지원
    - conversation_history: 최근 대화 목록 (시간순)
    - Agent B가 대화 흐름을 분석하여 사기 "가능성"을 판단

    응답에 MECE 카테고리 정보 포함:
    - category: A-1, B-2 등 (MECE 카테고리 코드)
    - category_name: 가족 사칭 (액정 파손) 등
    - scam_probability: 0-100 (사기 확률 %)
    """
    try:
        sender_id = str(request.sender_id) if request.sender_id else None
        user_id = str(request.receiver_id) if request.receiver_id else None

        # 대화 히스토리를 dict 리스트로 변환
        conversation_history = None
        if request.conversation_history:
            conversation_history = [
                {
                    "sender_id": msg.sender_id,
                    "message": msg.message,
                    "timestamp": msg.timestamp
                }
                for msg in request.conversation_history
            ]
            print(f"[API] 대화 히스토리 {len(conversation_history)}개 메시지 수신")

        result = analyze_incoming(
            request.text,
            sender_id=sender_id,
            user_id=user_id,
            conversation_history=conversation_history,  # 대화 맥락 전달
            use_ai=request.use_ai
        )

        # 메트릭 기록 (Agent B)
        if METRICS_ENABLED and kat_metrics:
            kat_metrics.record_agent_b_threat(
                risk_level=result.risk_level.value,
                category=result.category or "unknown"
            )
            if result.scam_probability:
                kat_metrics.record_scam_probability(result.scam_probability)

        return AnalysisResponse(
            risk_level=result.risk_level.value,
            reasons=result.reasons,
            recommended_action=result.recommended_action,
            is_secret_recommended=False,
            category=result.category,
            category_name=result.category_name,
            scam_probability=result.scam_probability
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 이미지 OCR 캐시 (image_url -> extracted_text)
_ocr_cache: dict = {}


class ImageAnalysisParams(BaseModel):
    use_ai: bool = False


class OCRRequest(BaseModel):
    image_url: str  # 이미지 URL 또는 경로


class OCRResponse(BaseModel):
    extracted_text: str
    cached: bool


class ImageTextAnalysisRequest(BaseModel):
    """이미지에서 추출된 텍스트로 분석 요청"""
    extracted_text: str
    use_ai: bool = True


@app.post("/api/agents/ocr", response_model=OCRResponse)
async def api_ocr_image(request: OCRRequest):
    """
    이미지 OCR - 텍스트 추출만 수행 (분석 없음)

    이미지 선택 시점에 호출하여 미리 OCR 수행
    결과는 캐싱되어 전송 시 빠르게 분석 가능
    """
    image_url = request.image_url

    # 캐시 확인
    if image_url in _ocr_cache:
        return OCRResponse(
            extracted_text=_ocr_cache[image_url],
            cached=True
        )

    try:
        # Vision 모델로 OCR
        from agent.llm.kanana import LLMManager

        vision_model = LLMManager.get("vision")
        if not vision_model:
            raise HTTPException(status_code=500, detail="Vision model not available")

        # 이미지 경로 처리 (URL이면 다운로드, 로컬이면 그대로)
        import os
        if image_url.startswith(('http://', 'https://')):
            # URL에서 다운로드
            import requests
            import tempfile
            response = requests.get(image_url)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
                f.write(response.content)
                image_path = f.name
        else:
            # 로컬 경로
            image_path = image_url
            if not os.path.exists(image_path):
                raise HTTPException(status_code=404, detail=f"Image not found: {image_path}")

        # OCR 수행
        extracted_text = vision_model.analyze_image(image_path)

        # 캐싱
        _ocr_cache[image_url] = extracted_text

        return OCRResponse(
            extracted_text=extracted_text,
            cached=False
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/analyze/text-from-image", response_model=AnalysisResponse)
async def api_analyze_text_from_image(request: ImageTextAnalysisRequest):
    """
    이미지에서 추출된 텍스트 분석

    OCR이 이미 완료된 텍스트를 받아 PII 분석만 수행
    이미지 전송 시 빠른 분석을 위해 사용
    """
    try:
        result = analyze_outgoing(request.extracted_text, use_ai=request.use_ai)
        return AnalysisResponse(
            risk_level=result.risk_level.value,
            reasons=result.reasons,
            recommended_action=result.recommended_action,
            is_secret_recommended=result.is_secret_recommended
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/analyze/image", response_model=AnalysisResponse)
async def api_analyze_image(
    file: UploadFile = File(...),
    use_ai: bool = True  # 기본값 True - 하이브리드 방식 (Rule-based + AI)
):
    """
    이미지 분석 - Vision OCR + PII 감지
    이미지에서 텍스트를 추출하고 민감정보를 분석합니다.

    순차 처리:
    1. Kanana Vision → 이미지에서 텍스트 추출
    2. 추출된 텍스트를 하이브리드 방식으로 분석 (Rule-based + AI)

    하이브리드 방식:
    - Rule-based 패턴 매칭 (항상 실행)
    - AI 분석 (use_ai=True일 때 추가 실행)
    - 둘 중 높은 위험도 사용
    """
    # 임시 파일로 저장
    temp_path = None
    try:
        # 파일 확장자 추출
        ext = Path(file.filename).suffix if file.filename else ".png"

        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        # MCP 도구로 분석 (순차 처리: Vision → Instruct/Rule-based)
        result = analyze_image(temp_path, use_ai=use_ai)

        return AnalysisResponse(
            risk_level=result.risk_level.value,
            reasons=result.reasons,
            recommended_action=result.recommended_action,
            is_secret_recommended=result.is_secret_recommended
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 임시 파일 정리
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


# === Secret Message Pydantic Models ===

class SecretMessageCreate(BaseModel):
    """시크릿 메시지 생성 요청"""
    room_id: int
    sender_id: int
    message: str
    message_type: str = "text"
    image_url: Optional[str] = None
    expiry_seconds: int = 60
    require_auth: bool = False
    prevent_capture: bool = True


class SecretMessageResponse(BaseModel):
    """시크릿 메시지 응답"""
    secret_id: str
    room_id: int
    sender_id: int
    message_type: str
    expiry_seconds: int
    require_auth: bool
    prevent_capture: bool
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


class SecretMessageContent(BaseModel):
    """시크릿 메시지 내용 (열람 시)"""
    secret_id: str
    message: str
    message_type: str
    image_url: Optional[str] = None
    is_expired: bool
    prevent_capture: bool
    remaining_seconds: int


# === Secret Message API ===

@app.post("/api/secret/create", response_model=SecretMessageResponse)
def create_secret_message(
    request: SecretMessageCreate,
    db: Session = Depends(get_db)
):
    """시크릿 메시지 생성"""
    secret_id = str(uuid.uuid4())
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=request.expiry_seconds)

    secret_msg = SecretMessageModel(
        secret_id=secret_id,
        room_id=request.room_id,
        sender_id=request.sender_id,
        original_message=request.message,
        message_type=request.message_type,
        image_url=request.image_url,
        expiry_seconds=request.expiry_seconds,
        require_auth=request.require_auth,
        prevent_capture=request.prevent_capture,
        created_at=now,
        expires_at=expires_at
    )

    db.add(secret_msg)
    db.commit()
    db.refresh(secret_msg)

    return SecretMessageResponse(
        secret_id=secret_msg.secret_id,
        room_id=secret_msg.room_id,
        sender_id=secret_msg.sender_id,
        message_type=secret_msg.message_type,
        expiry_seconds=secret_msg.expiry_seconds,
        require_auth=secret_msg.require_auth,
        prevent_capture=secret_msg.prevent_capture,
        created_at=secret_msg.created_at,
        expires_at=secret_msg.expires_at
    )


@app.get("/api/secret/view/{secret_id}", response_model=SecretMessageContent)
def view_secret_message(
    secret_id: str,
    db: Session = Depends(get_db)
):
    """시크릿 메시지 열람"""
    secret_msg = db.query(SecretMessageModel).filter(
        SecretMessageModel.secret_id == secret_id
    ).first()

    if not secret_msg:
        raise HTTPException(status_code=404, detail="메시지를 찾을 수 없습니다")

    now = datetime.utcnow()

    # 만료 체크
    if now > secret_msg.expires_at or secret_msg.is_expired:
        if not secret_msg.is_expired:
            secret_msg.is_expired = True
            db.commit()

        return SecretMessageContent(
            secret_id=secret_id,
            message="[만료된 메시지입니다]",
            message_type="text",
            image_url=None,
            is_expired=True,
            prevent_capture=secret_msg.prevent_capture,
            remaining_seconds=0
        )

    # 첫 열람 기록
    if not secret_msg.is_viewed:
        secret_msg.is_viewed = True
        secret_msg.viewed_at = now
        db.commit()

    remaining = (secret_msg.expires_at - now).total_seconds()
    remaining_seconds = max(0, int(remaining))

    return SecretMessageContent(
        secret_id=secret_id,
        message=secret_msg.original_message,
        message_type=secret_msg.message_type,
        image_url=secret_msg.image_url,
        is_expired=False,
        prevent_capture=secret_msg.prevent_capture,
        remaining_seconds=remaining_seconds
    )


@app.delete("/api/secret/expire/{secret_id}")
def expire_secret_message(
    secret_id: str,
    db: Session = Depends(get_db)
):
    """시크릿 메시지 수동 만료"""
    secret_msg = db.query(SecretMessageModel).filter(
        SecretMessageModel.secret_id == secret_id
    ).first()

    if not secret_msg:
        raise HTTPException(status_code=404, detail="메시지를 찾을 수 없습니다")

    secret_msg.is_expired = True
    secret_msg.original_message = "[삭제된 메시지]"
    db.commit()

    return {"status": "expired", "secret_id": secret_id}


@app.get("/api/secret/status/{secret_id}")
def check_secret_status(
    secret_id: str,
    db: Session = Depends(get_db)
):
    """시크릿 메시지 상태 확인"""
    secret_msg = db.query(SecretMessageModel).filter(
        SecretMessageModel.secret_id == secret_id
    ).first()

    if not secret_msg:
        raise HTTPException(status_code=404, detail="메시지를 찾을 수 없습니다")

    now = datetime.utcnow()
    is_expired = now > secret_msg.expires_at or secret_msg.is_expired
    remaining = max(0, (secret_msg.expires_at - now).total_seconds()) if not is_expired else 0

    return {
        "secret_id": secret_id,
        "is_viewed": secret_msg.is_viewed,
        "viewed_at": secret_msg.viewed_at,
        "is_expired": is_expired,
        "remaining_seconds": int(remaining),
        "created_at": secret_msg.created_at,
        "expires_at": secret_msg.expires_at
    }


if __name__ == "__main__":
    import uvicorn
    print("Starting DualGuard Agent API on port 8002...")
    print("Category fields: category, category_name, scam_probability enabled")
    print("Server reload triggered at startup")
    uvicorn.run(app, host="0.0.0.0", port=8002)
