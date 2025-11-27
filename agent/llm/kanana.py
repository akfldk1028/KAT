"""
Kanana LLM Manager
LLM 인스턴스를 딕셔너리로 관리하는 Singleton 패턴

특징:
- Lazy Loading: 요청 시에만 모델 로드
- Singleton: 동일 모델 재사용으로 메모리 절약
- 확장성: 새 모델 타입 추가 용이
- ReAct 패턴: 도구 호출 지원 (analyze_with_tools)
- Vision: API 호출 방식 (Kanana-1.5-v-3b)
"""
from typing import Dict, Optional, Callable, Any
import re
import json
import os
import base64
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드 (backend/.env)
env_path = Path(__file__).parent.parent.parent / "backend" / ".env"
load_dotenv(env_path)

# Configuration: "4bit", "8bit", or None (for 16-bit/32-bit)
DEFAULT_QUANTIZATION = "8bit"

# Vision API 설정 - 환경변수에서 로드
VISION_API_KEY = os.getenv("KANANA_VISION_API_KEY") or os.getenv("OPENAI_API_KEY")
VISION_API_BASE = os.getenv("KANANA_VISION_BASE_URL") or os.getenv("OPENAI_API_BASE")
VISION_MODEL = os.getenv("KANANA_VISION_MODEL", "kanana-1.5-v-3b")

class KananaLLM:
    """Kanana LLM Wrapper"""

    def __init__(self, model_type: str = "instruct", quantization: str = DEFAULT_QUANTIZATION):
        """
        Initialize Kanana LLM
        Args:
            model_type: "instruct" for general chat, "safeguard" for safety detection, "vision" for OCR
            quantization: "4bit", "8bit", or None
        """
        # Lazy imports for heavy dependencies
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        try:
            from transformers import AutoModelForVision2Seq, AutoProcessor
        except ImportError:
            pass # Vision dependencies might not be needed for text models
            
        import torch

        if model_type == "safeguard":
            self.model_id = "kakaocorp/kanana-safeguard-8b"
            self.is_safeguard = True
            self.is_vision = False
        elif model_type == "vision":
            # Kanana 1.5 Vision - API 방식
            self.model_id = VISION_MODEL
            self.is_safeguard = False
            self.is_vision = True
        else:
            # 로컬 Instruct 모델
            self.model_id = "./model"
            self.is_safeguard = False
            self.is_vision = False

        self.tokenizer = None
        self.processor = None
        self.model = None
        self.vision_client = None  # Vision API 클라이언트
        self._torch = None

        # Vision은 API 방식이므로 별도 처리
        if self.is_vision:
            print(f"Kanana Vision ({model_type}) initializing with API...")
            try:
                from openai import OpenAI
                self.vision_client = OpenAI(
                    api_key=VISION_API_KEY,
                    base_url=VISION_API_BASE,
                )
                self.model = "API"  # 모델 로드 성공 표시
                print(f"Kanana Vision API client initialized successfully!")
            except Exception as e:
                print(f"Failed to initialize Vision API client: {e}")
            return  # Vision은 여기서 끝

        # 텍스트 모델 (instruct, safeguard)은 로컬 로드
        import torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._torch = torch
        print(f"Kanana LLM ({model_type}) initializing on {self.device} with {quantization} quantization...")

        try:
            # Prepare Quantization Config
            quantization_config = None
            if self.device == "cuda" and quantization:
                if quantization == "8bit":
                    quantization_config = BitsAndBytesConfig(load_in_8bit=True)
                elif quantization == "4bit":
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.bfloat16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )

            # Load Tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)

            # Determine dtype
            dtype = torch.bfloat16 if self.device == "cuda" else torch.float32

            # Text Model Loading
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=dtype,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True
            )

            print(f"Kanana LLM ({model_type}) Loaded Successfully!")
        except Exception as e:
            print(f"Failed to load Kanana LLM: {e}")
            print("Running in fallback mode (Rule-based only).")

    def analyze(self, text: str) -> str:
        """일반 텍스트 분석 (Instruct 모델용)"""
        if not self.model or not self.tokenizer:
            return "Kanana Analysis: Model not loaded (Fallback)"

        try:
            prompt = f"""
            분석 요청: 다음 메시지가 피싱이나 사기일 가능성이 있는지 분석해줘.
            메시지: "{text}"

            분석 결과:
            """

            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.7
            )
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            if "분석 결과:" in response:
                return response.split("분석 결과:")[1].strip()
            return response

        except Exception as e:
            return f"Kanana Analysis Error: {str(e)}"

    def classify_safety(self, user_prompt: str, assistant_prompt: str = "") -> dict:
        """
        Kanana Safeguard 모델로 안전성 분류
        Returns: {"is_safe": bool, "category": str, "raw_output": str}
        """
        if not self.is_safeguard:
            return {"is_safe": True, "category": "N/A", "raw_output": "Not a safeguard model"}

        if not self.model or not self.tokenizer:
            return {"is_safe": True, "category": "FALLBACK", "raw_output": "Model not loaded"}

        try:
            messages = [
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_prompt}
            ]

            input_ids = self.tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                return_tensors="pt"
            ).to(self.device)

            attention_mask = (input_ids != self.tokenizer.pad_token_id).long()

            with self._torch.no_grad():
                output_ids = self.model.generate(
                    input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=1,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            gen_idx = input_ids.shape[-1]
            result = self.tokenizer.decode(output_ids[0][gen_idx], skip_special_tokens=True)

            is_safe = result.startswith("<SAFE>")
            category = "SAFE" if is_safe else result.replace("<", "").replace(">", "")

            return {
                "is_safe": is_safe,
                "category": category,
                "raw_output": result
            }

        except Exception as e:
            return {
                "is_safe": True,
                "category": "ERROR",
                "raw_output": f"Safeguard Error: {str(e)}"
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

        if not self.vision_client:
            return "Error: Vision API client not initialized."

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
            response = self.vision_client.chat.completions.create(
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

    def analyze_with_tools(
        self,
        user_message: str,
        system_prompt: str,
        tools: Dict[str, Callable[..., Any]],
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        ReAct 패턴으로 도구를 호출하며 분석

        Args:
            user_message: 사용자 메시지
            system_prompt: 시스템 프롬프트 (도구 설명 포함)
            tools: 사용 가능한 도구들 {"tool_name": callable}
            max_iterations: 최대 반복 횟수

        Returns:
            최종 분석 결과 딕셔너리
        """
        if not self.model or not self.tokenizer:
            return {
                "risk_level": "LOW",
                "detected_pii": [],
                "reasons": ["Model not loaded"],
                "is_secret_recommended": False,
                "recommended_action": "전송"
            }

        try:
            # 대화 히스토리 구성
            conversation = f"{system_prompt}\n\nUser: {user_message}\n\n"

            for iteration in range(max_iterations):
                # LLM 호출
                inputs = self.tokenizer(conversation, return_tensors="pt").to(self.device)

                with self._torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=512,
                        temperature=0.1,  # 낮은 temperature로 일관성 있는 응답
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id,
                        eos_token_id=self.tokenizer.eos_token_id
                    )

                response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

                # 입력 프롬프트 제거하고 새 생성 부분만 추출
                new_content = response[len(conversation):].strip()

                # Answer 찾기 (최종 응답)
                answer_match = re.search(r'Answer:\s*(\{.*?\})', new_content, re.DOTALL)
                if answer_match:
                    try:
                        result = json.loads(answer_match.group(1))
                        return result
                    except json.JSONDecodeError:
                        pass

                # Action 파싱
                action_match = re.search(r'Action:\s*(\w+)', new_content)
                action_input_match = re.search(r'Action Input:\s*(\{.*?\})', new_content, re.DOTALL)

                if action_match and action_input_match:
                    action_name = action_match.group(1)
                    try:
                        action_input = json.loads(action_input_match.group(1))
                    except json.JSONDecodeError:
                        action_input = {}

                    # 도구 실행
                    if action_name in tools:
                        tool_result = tools[action_name](**action_input)
                        observation = json.dumps(tool_result, ensure_ascii=False)
                    else:
                        observation = f"Error: Unknown tool '{action_name}'"

                    # 대화에 결과 추가
                    conversation += f"{new_content}\nObservation: {observation}\n"
                else:
                    # Action도 Answer도 없으면 기본 응답 반환
                    break

            # 최대 반복 후에도 Answer가 없으면 기본 응답
            return {
                "risk_level": "LOW",
                "detected_pii": [],
                "reasons": ["분석 완료"],
                "is_secret_recommended": False,
                "recommended_action": "전송"
            }

        except Exception as e:
            return {
                "risk_level": "LOW",
                "detected_pii": [],
                "reasons": [f"분석 오류: {str(e)}"],
                "is_secret_recommended": False,
                "recommended_action": "전송"
            }


class LLMManager:
    """
    LLM 인스턴스 관리자
    Singleton 패턴으로 모델 재사용

    GPU 메모리 제한으로 한 번에 하나의 모델만 로드 가능
    - sequential_mode=True: 모델 변경 시 기존 모델 언로드 (기본)
    - sequential_mode=False: 여러 모델 동시 로드 시도 (충분한 VRAM 필요)
    """

    _instances: Dict[str, KananaLLM] = {}
    _current_model: Optional[str] = None  # 현재 로드된 모델 타입
    sequential_mode: bool = True  # GPU 메모리 절약을 위해 순차 모드 기본값

    @classmethod
    def get(cls, model_type: str = "safeguard", quantization: str = DEFAULT_QUANTIZATION) -> Optional[KananaLLM]:
        """
        LLM 인스턴스 가져오기 (Lazy Loading)

        Args:
            model_type: "instruct", "safeguard", or "vision"
            quantization: "4bit", "8bit", or None

        Returns:
            KananaLLM 인스턴스 또는 None (로드 실패 시)
        """
        # 순차 모드: 다른 모델이 로드되어 있으면 언로드
        if cls.sequential_mode and cls._current_model and cls._current_model != model_type:
            print(f"[LLMManager] Sequential mode: Unloading {cls._current_model} to load {model_type}...")
            cls.unload(cls._current_model)

        if model_type not in cls._instances:
            print(f"[LLMManager] Loading {model_type} model for the first time...")
            cls._instances[model_type] = KananaLLM(model_type=model_type, quantization=quantization)

        llm = cls._instances[model_type]

        if llm.model is None:
            print(f"[LLMManager] {model_type} model failed to load (Model is None). Returning None.")
            return None

        # Vision은 API 클라이언트, 텍스트 모델은 tokenizer 체크
        if llm.is_vision:
            if llm.vision_client is None:
                print(f"[LLMManager] {model_type} model failed to load (Vision client is None). Returning None.")
                return None
        elif llm.tokenizer is None:
            print(f"[LLMManager] {model_type} model failed to load (Tokenizer is None). Returning None.")
            return None

        cls._current_model = model_type
        return llm

    @classmethod
    def is_loaded(cls, model_type: str) -> bool:
        """특정 모델이 로드되었는지 확인"""
        return model_type in cls._instances

    @classmethod
    def unload(cls, model_type: str) -> None:
        """특정 모델 언로드 (메모리 해제)"""
        if model_type in cls._instances:
            del cls._instances[model_type]
            if cls._current_model == model_type:
                cls._current_model = None
            import gc
            import torch
            gc.collect()
            torch.cuda.empty_cache()
            print(f"[LLMManager] {model_type} model unloaded and memory cleared.")

    @classmethod
    def unload_all(cls) -> None:
        """모든 모델 언로드"""
        cls._instances.clear()
        cls._current_model = None
        import gc
        import torch
        gc.collect()
        torch.cuda.empty_cache()
        print("[LLMManager] All models unloaded.")
