"""
Kanana LLM Manager
LLM 인스턴스를 딕셔너리로 관리하는 Singleton 패턴

특징:
- Lazy Loading: 요청 시에만 모델 로드
- Singleton: 동일 모델 재사용으로 메모리 절약
- 확장성: 새 모델 타입 추가 용이
- API 방식: Kanana-2-30b OpenAI 호환 API 사용 (Tool Call 지원)
- Vision: API 호출 방식 (Kanana-1.5-v-3b)
"""
from typing import Dict, Optional, Callable, Any, List
import re
import json
import os
import base64
from pathlib import Path
from dotenv import load_dotenv

# MCP 클라이언트는 순환 import 방지를 위해 함수 내부에서 lazy import

# .env 파일 로드 (backend/.env)
env_path = Path(__file__).parent.parent.parent / "backend" / ".env"
load_dotenv(env_path)

# LLM API 설정 - Kanana-2-30b (2025-11-28 업데이트)
LLM_API_KEY = os.getenv("KANANA_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
LLM_API_BASE = os.getenv("KANANA_LLM_BASE_URL") or os.getenv("OPENAI_API_BASE")

# Vision API 설정 - Kanana-1.5-v-3b
VISION_API_KEY = os.getenv("KANANA_VISION_API_KEY") or os.getenv("OPENAI_API_KEY")
VISION_API_BASE = os.getenv("KANANA_VISION_BASE_URL") or os.getenv("OPENAI_API_BASE")
VISION_MODEL = os.getenv("KANANA_VISION_MODEL", "kanana-1.5-v-3b")


class KananaLLM:
    """Kanana LLM Wrapper - API 방식"""

    def __init__(self, model_type: str = "instruct"):
        """
        Initialize Kanana LLM
        Args:
            model_type: "instruct" for general chat with tool call, "vision" for OCR
        """
        self.model_type = model_type
        self.client = None
        self.model_id = None
        self.is_vision = model_type == "vision"

        if self.is_vision:
            # Vision API 클라이언트
            print(f"[KananaLLM] Vision API 초기화 중...")
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=VISION_API_KEY,
                    base_url=VISION_API_BASE,
                )
                self.model_id = VISION_MODEL
                print(f"[KananaLLM] Vision API 초기화 성공!")
            except Exception as e:
                print(f"[KananaLLM] Vision API 초기화 실패: {e}")
        else:
            # LLM API 클라이언트 (Kanana-2-30b)
            print(f"[KananaLLM] LLM API 초기화 중 (Kanana-2-30b)...")
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=LLM_API_KEY,
                    base_url=LLM_API_BASE,
                )
                # 모델 ID 자동 감지
                models = self.client.models.list()
                if models.data:
                    self.model_id = models.data[0].id
                    print(f"[KananaLLM] LLM API 초기화 성공! Model: {self.model_id}")
                else:
                    print(f"[KananaLLM] 모델 목록이 비어있음")
            except Exception as e:
                print(f"[KananaLLM] LLM API 초기화 실패: {e}")

    def is_ready(self) -> bool:
        """API 클라이언트가 준비되었는지 확인"""
        return self.client is not None and self.model_id is not None

    def analyze(self, text: str, system_prompt: str = None) -> str:
        """일반 텍스트 분석 (API 방식)"""
        if not self.is_ready():
            return "Kanana Analysis: API not ready (Fallback)"

        if system_prompt is None:
            system_prompt = "당신은 카카오에서 개발된 친절한 AI입니다."

        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1,
                max_tokens=512
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Kanana Analysis Error: {str(e)}"

    def analyze_with_tools(
        self,
        user_message: str,
        system_prompt: str,
        tools: Dict[str, Callable[..., Any]],
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        OpenAI Tool Call 방식으로 도구를 호출하며 분석

        Args:
            user_message: 사용자 메시지
            system_prompt: 시스템 프롬프트
            tools: 사용 가능한 도구들 {"tool_name": callable}
            max_iterations: 최대 반복 횟수

        Returns:
            최종 분석 결과 딕셔너리
        """
        if not self.is_ready():
            return {
                "risk_level": "LOW",
                "detected_pii": [],
                "reasons": ["API not ready"],
                "is_secret_recommended": False,
                "recommended_action": "전송"
            }

        # OpenAI 형식의 도구 정의
        tool_definitions = self._build_tool_definitions(tools)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            for iteration in range(max_iterations):
                # API 호출
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    tools=tool_definitions if tool_definitions else None,
                    tool_choice="auto" if tool_definitions else None,
                    temperature=0.1,
                    max_tokens=1024
                )

                assistant_message = response.choices[0].message

                # Tool call이 있는 경우
                if assistant_message.tool_calls:
                    messages.append(assistant_message)

                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            tool_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            tool_args = {}

                        # 도구 실행
                        if tool_name in tools:
                            try:
                                tool_result = tools[tool_name](**tool_args)
                                result_str = json.dumps(tool_result, ensure_ascii=False)
                            except Exception as e:
                                result_str = f"Error: {str(e)}"
                        else:
                            result_str = f"Unknown tool: {tool_name}"

                        # 도구 결과 추가
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_str
                        })
                else:
                    # 최종 응답
                    content = assistant_message.content or ""

                    # JSON 파싱 시도
                    result = self._parse_response(content)
                    if result:
                        return result

                    # JSON이 없으면 내용 기반으로 결과 생성
                    return self._extract_result_from_text(content, user_message)

            # max_iterations 초과
            return {
                "risk_level": "LOW",
                "detected_pii": [],
                "reasons": ["분석 완료 (max iterations)"],
                "is_secret_recommended": False,
                "recommended_action": "전송"
            }

        except Exception as e:
            print(f"[KananaLLM] analyze_with_tools 오류: {e}")
            return {
                "risk_level": "LOW",
                "detected_pii": [],
                "reasons": [f"분석 오류: {str(e)}"],
                "is_secret_recommended": False,
                "recommended_action": "전송"
            }

    def _build_tool_definitions(self, tools: Dict[str, Callable]) -> List[dict]:
        """도구 정의를 OpenAI 형식으로 변환"""
        definitions = []

        tool_schemas = {
            "scan_pii": {
                "name": "scan_pii",
                "description": "텍스트에서 개인정보(PII)를 탐지합니다. 계좌번호, 주민번호, 전화번호, 이메일 등을 찾습니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "분석할 텍스트"}
                    },
                    "required": ["text"]
                }
            },
            "evaluate_risk": {
                "name": "evaluate_risk",
                "description": "탐지된 PII 목록을 기반으로 위험도를 평가합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "found_pii": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "탐지된 PII 목록"
                        }
                    },
                    "required": ["found_pii"]
                }
            },
            "analyze_full": {
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
        }

        for tool_name in tools.keys():
            if tool_name in tool_schemas:
                definitions.append({
                    "type": "function",
                    "function": tool_schemas[tool_name]
                })

        return definitions

    def _parse_response(self, content: str) -> Optional[Dict[str, Any]]:
        """응답에서 JSON 결과 파싱"""
        # JSON 블록 찾기
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'\{[^{}]*"risk_level"[^{}]*\}',
            r'\{.*?\}'
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                try:
                    result = json.loads(match)
                    if "risk_level" in result:
                        return result
                except json.JSONDecodeError:
                    continue

        return None

    def _extract_result_from_text(self, content: str, user_message: str) -> Dict[str, Any]:
        """텍스트 응답에서 결과 추출"""
        content_lower = content.lower()

        # 위험도 추출
        risk_level = "LOW"
        if "high" in content_lower or "높" in content_lower or "위험" in content_lower:
            risk_level = "HIGH"
        elif "medium" in content_lower or "중간" in content_lower:
            risk_level = "MEDIUM"

        # 시크릿 추천 여부
        is_secret = risk_level in ["HIGH", "MEDIUM"] or \
                    "시크릿" in content_lower or \
                    "secret" in content_lower or \
                    "민감" in content_lower

        return {
            "risk_level": risk_level,
            "detected_pii": [],
            "reasons": [content[:200] if content else "분석 완료"],
            "is_secret_recommended": is_secret,
            "recommended_action": "시크릿 전송 권장" if is_secret else "전송"
        }

    def analyze_with_mcp(
        self,
        user_message: str,
        system_prompt: str,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        MCP 프로토콜을 통해 도구를 호출하며 분석

        Kanana LLM이 MCP 클라이언트 역할:
        1. LLM이 Tool Call 요청 생성
        2. MCP Client가 MCP 서버의 도구 호출
        3. 결과를 LLM에 전달
        4. LLM이 최종 분석 결과 반환

        Args:
            user_message: 사용자 메시지
            system_prompt: 시스템 프롬프트
            max_iterations: 최대 반복 횟수

        Returns:
            최종 분석 결과 딕셔너리
        """
        if not self.is_ready():
            return {
                "risk_level": "LOW",
                "detected_pii": [],
                "reasons": ["API not ready"],
                "is_secret_recommended": False,
                "recommended_action": "전송"
            }

        # MCP 클라이언트에서 도구 스키마 가져오기 (lazy import)
        from ..mcp.client import get_mcp_client
        mcp_client = get_mcp_client()
        tool_definitions = mcp_client.get_openai_tools_schema()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            for iteration in range(max_iterations):
                print(f"[KananaLLM+MCP] Iteration {iteration + 1}/{max_iterations}")

                # API 호출
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    tools=tool_definitions if tool_definitions else None,
                    tool_choice="auto" if tool_definitions else None,
                    temperature=0.1,
                    max_tokens=1024
                )

                assistant_message = response.choices[0].message

                # Tool call이 있는 경우 - MCP를 통해 도구 호출
                if assistant_message.tool_calls:
                    messages.append(assistant_message)

                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            tool_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            tool_args = {}

                        print(f"[KananaLLM+MCP] Tool Call: {tool_name}({tool_args})")

                        # MCP 클라이언트를 통해 도구 호출
                        tool_result = mcp_client.call_tool(tool_name, tool_args)
                        result_str = json.dumps(tool_result, ensure_ascii=False)

                        print(f"[KananaLLM+MCP] Tool Result: {result_str[:200]}...")

                        # 도구 결과 추가
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_str
                        })
                else:
                    # 최종 응답
                    content = assistant_message.content or ""

                    # JSON 파싱 시도
                    result = self._parse_response(content)
                    if result:
                        return result

                    # JSON이 없으면 내용 기반으로 결과 생성
                    return self._extract_result_from_text(content, user_message)

            # max_iterations 초과
            return {
                "risk_level": "LOW",
                "detected_pii": [],
                "reasons": ["분석 완료 (max iterations)"],
                "is_secret_recommended": False,
                "recommended_action": "전송"
            }

        except Exception as e:
            print(f"[KananaLLM+MCP] 오류: {e}")
            return {
                "risk_level": "LOW",
                "detected_pii": [],
                "reasons": [f"분석 오류: {str(e)}"],
                "is_secret_recommended": False,
                "recommended_action": "전송"
            }

    def analyze_image(self, image_path: str, prompt: str = None) -> str:
        """
        Kanana Vision API로 이미지 분석 (OCR)

        Args:
            image_path: 이미지 파일 경로
            prompt: 커스텀 프롬프트 (기본: OCR 프롬프트)

        Returns:
            추출된 텍스트
        """
        if not self.is_vision:
            return "Error: This is not a vision model."

        if not self.is_ready():
            return "Error: Vision API not ready."

        if prompt is None:
            prompt = """이 이미지에서 모든 텍스트를 추출해주세요.
텍스트가 있다면 그대로 출력하고, 텍스트가 없다면 "텍스트 없음"이라고 답해주세요.
개인정보(계좌번호, 주민번호, 전화번호, 주소 등)가 보이면 그것도 포함해서 추출해주세요."""

        try:
            if not os.path.exists(image_path):
                return f"Error: Image file not found at {image_path}"

            # 이미지를 base64로 인코딩
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

            # 이미지 확장자로 MIME 타입 결정
            ext = Path(image_path).suffix.lower()
            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            mime_type = mime_types.get(ext, "image/png")

            # API 호출
            response = self.client.chat.completions.create(
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            },
                        },
                    ],
                }],
                model=self.model_id,
                max_completion_tokens=2048,
                extra_body={"add_generation_prompt": True, "stop_token_ids": [128001]},
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Vision API Error: {str(e)}"


class LLMManager:
    """
    LLM 인스턴스 관리자
    Singleton 패턴으로 모델 재사용
    API 방식이므로 메모리 부담 없음
    """

    _instances: Dict[str, KananaLLM] = {}

    @classmethod
    def get(cls, model_type: str = "instruct") -> Optional[KananaLLM]:
        """
        LLM 인스턴스 가져오기 (Lazy Loading)

        Args:
            model_type: "instruct" (Kanana-2-30b) or "vision" (Kanana-1.5-v-3b)

        Returns:
            KananaLLM 인스턴스 또는 None (초기화 실패 시)
        """
        if model_type not in cls._instances:
            print(f"[LLMManager] {model_type} API 클라이언트 초기화 중...")
            cls._instances[model_type] = KananaLLM(model_type=model_type)

        llm = cls._instances[model_type]

        if not llm.is_ready():
            print(f"[LLMManager] {model_type} API가 준비되지 않음")
            return None

        return llm

    @classmethod
    def is_loaded(cls, model_type: str) -> bool:
        """특정 모델이 로드되었는지 확인"""
        if model_type not in cls._instances:
            return False
        return cls._instances[model_type].is_ready()

    @classmethod
    def unload(cls, model_type: str) -> None:
        """특정 모델 인스턴스 제거"""
        if model_type in cls._instances:
            del cls._instances[model_type]
            print(f"[LLMManager] {model_type} 인스턴스 제거됨")

    @classmethod
    def unload_all(cls) -> None:
        """모든 모델 인스턴스 제거"""
        cls._instances.clear()
        print("[LLMManager] 모든 인스턴스 제거됨")
