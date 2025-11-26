import sys
import os
# Add project root to sys.path to allow importing 'agent'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from fastapi import APIRouter, HTTPException
# Import tools directly for POC (Internal MCP usage)
from agent import analyze_outgoing, analyze_incoming, AnalysisRequest, AnalysisResponse

router = APIRouter()

@router.post("/analyze/outgoing", response_model=AnalysisResponse)
async def api_analyze_outgoing(request: AnalysisRequest):
    try:
        # Calling the tool function directly. 
        # Since it's decorated with @mcp.tool, we might need to call it as a regular function 
        # or invoke it through the mcp context if needed. 
        # FastMCP tools are usually callable as regular functions too.
        result = analyze_outgoing(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/incoming", response_model=AnalysisResponse)
async def api_analyze_incoming(request: AnalysisRequest):
    try:
        result = analyze_incoming(request.text, request.sender_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/image", response_model=AnalysisResponse)
async def api_analyze_image(request: AnalysisRequest):
    # For POC, we assume the 'text' field contains the image path
    # In a real app, we would handle file upload via Multipart
    try:
        # Import here to avoid circular dependency if any, or just use the tool
        from agent import analyze_image
        result = analyze_image(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

