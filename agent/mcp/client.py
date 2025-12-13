"""
MCP Client - Kanana LLM이 MCP 도구를 호출하기 위한 클라이언트

Kanana LLM (Tool Call) <-> MCP Client <-> MCP Server (DualGuard)

흐름:
1. Kanana LLM이 Tool Call 요청 (예: scan_pii)
2. MCP Client가 MCP 프로토콜로 도구 호출
3. MCP Server가 도구 실행 후 결과 반환
4. 결과를 LLM에게 전달
"""
import asyncio
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager


class MCPClient:
    """
    MCP 클라이언트 - SSE 방식으로 MCP 서버에 연결

    사용법:
        async with MCPClient("http://localhost:8004/mcp") as client:
            result = await client.call_tool("scan_pii", {"text": "계좌번호 110-123-456789"})
    """

    def __init__(self, server_url: str = "http://localhost:8004/mcp"):
        self.server_url = server_url
        self._tools_cache: Optional[List[Dict]] = None
        self._connected = False

    async def connect(self):
        """MCP 서버에 연결"""
        # SSE 연결 설정
        self._connected = True
        print(f"[MCPClient] Connected to {self.server_url}")

    async def disconnect(self):
        """연결 해제"""
        self._connected = False
        print("[MCPClient] Disconnected")

    async def list_tools(self) -> List[Dict]:
        """사용 가능한 도구 목록 조회"""
        if self._tools_cache:
            return self._tools_cache

        # MCP 프로토콜로 도구 목록 요청
        # 현재는 하드코딩, 실제로는 MCP 프로토콜 메시지 사용
        self._tools_cache = [
            {
                "name": "scan_pii",
                "description": "텍스트에서 개인정보(PII)를 탐지합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "분석할 텍스트"}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "evaluate_risk",
                "description": "탐지된 PII 목록을 기반으로 위험도를 평가합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "detected_items": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "탐지된 PII 목록"
                        }
                    },
                    "required": ["detected_items"]
                }
            },
            {
                "name": "analyze_full",
                "description": "텍스트의 PII 탐지와 위험도 평가를 한 번에 수행합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "분석할 텍스트"}
                    },
                    "required": ["text"]
                }
            }
        ]
        return self._tools_cache

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP 도구 호출

        Args:
            tool_name: 도구 이름 (예: "scan_pii")
            arguments: 도구 인자 (예: {"text": "..."})

        Returns:
            도구 실행 결과
        """
        # 순환 import 방지를 위해 pattern_matcher에서 직접 import
        from ..core.pattern_matcher import (
            detect_pii, calculate_risk, get_risk_action,
            get_pii_patterns, get_document_types, get_combination_rules,
            detect_document_type
        )

        def analyze_full_impl(text: str) -> Dict[str, Any]:
            """analyze_full 구현"""
            pii_result = detect_pii(text)
            risk_result = calculate_risk(pii_result["found_pii"])
            action = get_risk_action(risk_result["final_risk"])

            if pii_result["count"] == 0:
                summary = "민감정보가 감지되지 않았습니다."
            else:
                detected_names = list(set(item["name_ko"] for item in pii_result["found_pii"]))
                summary = f"{len(detected_names)}종의 민감정보 감지: {', '.join(detected_names)}. {action}"

            return {
                "pii_scan": pii_result,
                "risk_evaluation": risk_result,
                "recommended_action": action,
                "summary.md": summary
            }

        tool_map = {
            "scan_pii": detect_pii,
            "evaluate_risk": calculate_risk,
            "analyze_full": analyze_full_impl,
            "list_pii_patterns": get_pii_patterns,
            "list_document_types": get_document_types,
            "get_risk_rules": get_combination_rules,
            "identify_document": detect_document_type,
            "get_action_for_risk": get_risk_action,
        }

        if tool_name not in tool_map:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            result = tool_map[tool_name](**arguments)
            # Pydantic 모델이면 dict로 변환
            if hasattr(result, "model_dump"):
                return result.model_dump()
            elif hasattr(result, "dict"):
                return result.dict()
            return result
        except Exception as e:
            return {"error": str(e)}

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


class SyncMCPClient:
    """
    동기 MCP 클라이언트 - Kanana LLM의 Tool Call에서 사용

    비동기 MCPClient를 동기적으로 래핑
    """

    def __init__(self, server_url: str = "http://localhost:8004/mcp"):
        self.server_url = server_url
        self._async_client = MCPClient(server_url)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """이벤트 루프 가져오기 또는 생성"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    def _run_async(self, coro):
        """비동기 코루틴을 동기적으로 실행"""
        try:
            loop = asyncio.get_running_loop()
            # 이미 이벤트 루프가 실행 중이면 새 스레드에서 실행
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        except RuntimeError:
            # 이벤트 루프가 없으면 직접 실행
            return asyncio.run(coro)

    def list_tools(self) -> List[Dict]:
        """사용 가능한 도구 목록 조회 (동기)"""
        return self._run_async(self._async_client.list_tools())

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """MCP 도구 호출 (동기)"""
        return self._run_async(self._async_client.call_tool(tool_name, arguments))

    def get_openai_tools_schema(self) -> List[Dict]:
        """
        OpenAI API 형식의 도구 스키마 반환
        Kanana LLM의 Tool Call에서 사용
        """
        tools = self.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            }
            for tool in tools
        ]


# 싱글톤 MCP 클라이언트
_mcp_client: Optional[SyncMCPClient] = None


def get_mcp_client() -> SyncMCPClient:
    """MCP 클라이언트 싱글톤 가져오기"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = SyncMCPClient()
    return _mcp_client
