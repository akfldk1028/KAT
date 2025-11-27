import sys
import os
# Add project root to sys.path to allow importing 'agent'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from fastapi import APIRouter, HTTPException
# Import tools directly for POC (Internal MCP usage)
from agent import analyze_outgoing, analyze_incoming, analyze_image, AnalysisRequest, AnalysisResponse

router = APIRouter()


def to_response(result) -> AnalysisResponse:
    """AnalysisResult를 AnalysisResponse로 변환"""
    return AnalysisResponse(
        risk_level=result.risk_level.value,
        reasons=result.reasons,
        recommended_action=result.recommended_action,
        is_secret_recommended=result.is_secret_recommended,
        detected_pii=result.detected_pii,
        extracted_text=result.extracted_text,
    )


@router.post("/analyze/outgoing", response_model=AnalysisResponse)
async def api_analyze_outgoing(request: AnalysisRequest):
    try:
        result = analyze_outgoing(request.text)
        return to_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/incoming", response_model=AnalysisResponse)
async def api_analyze_incoming(request: AnalysisRequest):
    try:
        result = analyze_incoming(request.text, request.sender_id)
        return to_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/image", response_model=AnalysisResponse)
async def api_analyze_image(request: AnalysisRequest):
    try:
        result = analyze_image(request.text)
        return to_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

