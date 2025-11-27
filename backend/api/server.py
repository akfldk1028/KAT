"""
FastAPI Agent API Server
MCP 도구를 HTTP 엔드포인트로 노출

포트: 8002
엔드포인트:
- POST /api/agents/analyze/outgoing - 발신 메시지 분석
- POST /api/agents/analyze/incoming - 수신 메시지 분석
- POST /api/agents/analyze/image - 이미지 분석 (Vision OCR + PII 감지)
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

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import tempfile
import shutil

# MCP 도구 임포트
from agent.mcp.tools import analyze_outgoing, analyze_incoming, analyze_image
from agent.core.models import RiskLevel

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


# === Request/Response 모델 ===

class OutgoingRequest(BaseModel):
    text: str
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    use_ai: bool = True  # Kanana LLM 사용 (테스트용 기본값 True)


class IncomingRequest(BaseModel):
    text: str
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None
    use_ai: bool = True  # Kanana LLM 사용 (테스트용 기본값 True)


class AnalysisResponse(BaseModel):
    risk_level: str
    reasons: List[str]
    recommended_action: str
    is_secret_recommended: bool


# === 엔드포인트 ===

@app.get("/api/agents/health")
async def health_check():
    """헬스체크"""
    return {"status": "ok", "service": "DualGuard Agent API"}


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
    """
    try:
        sender_id = str(request.sender_id) if request.sender_id else None
        result = analyze_incoming(
            request.text,
            sender_id=sender_id,
            use_ai=request.use_ai
        )
        return AnalysisResponse(
            risk_level=result.risk_level.value,
            reasons=result.reasons,
            recommended_action=result.recommended_action,
            is_secret_recommended=False
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
    use_ai: bool = False  # Query parameter로 전달
):
    """
    이미지 분석 - Vision OCR + PII 감지
    이미지에서 텍스트를 추출하고 민감정보를 분석합니다.

    순차 처리:
    1. Kanana Vision → 이미지에서 텍스트 추출
    2. 추출된 텍스트를 rule-based 또는 AI로 분석

    use_ai=True: Kanana Instruct로 ReAct 분석
    use_ai=False: Rule-based 패턴 매칭 (기본값)
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


if __name__ == "__main__":
    import uvicorn
    print("Starting DualGuard Agent API on port 8002...")
    uvicorn.run(app, host="0.0.0.0", port=8002)
