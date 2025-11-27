"""
Kanana LLM Manager
LLM 인스턴스를 딕셔너리로 관리하는 Singleton 패턴

특징:
- Lazy Loading: 요청 시에만 모델 로드
- Singleton: 동일 모델 재사용으로 메모리 절약
- 확장성: 새 모델 타입 추가 용이
- ReAct 패턴: 도구 호출 지원 (analyze_with_tools)
"""
from typing import Dict, Optional, Callable, Any
import re
import json

# Configuration: "4bit", "8bit", or None (for 16-bit/32-bit)
DEFAULT_QUANTIZATION = "8bit"

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
            # Kanana 1.5 Vision (OCR/VLM)
            self.model_id = "./model_vision"
            self.is_safeguard = False
            self.is_vision = True
        else:
            # User requested update to Kanana 1.5 and local storage
            # The model will be moved to the 'model' directory in the project root
            self.model_id = "./model"
            self.is_safeguard = False
            self.is_vision = False

        self.tokenizer = None
        self.processor = None # For vision model
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._torch = torch  # Store reference for later use
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

            # Load Tokenizer / Processor
            if self.is_vision:
                self.processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=True)
            else:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)

            # Determine dtype
            dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
            
            # Load Model
            if self.is_vision:
                # Vision Model Loading
                # Note: Vision model does NOT support quantization (no official bitsandbytes support)
                # See: https://huggingface.co/kakaocorp/kanana-1.5-v-3b-instruct#requirements
                self.model = AutoModelForVision2Seq.from_pretrained(
                    self.model_id,
                    torch_dtype=dtype,
                    # quantization_config=None for Vision model (not supported)
                    device_map="auto",
                    trust_remote_code=True,
                    _attn_implementation="eager"
                )
            else:
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

    def analyze_image(self, image_path: str, prompt: str = "사진에서 텍스트를 추출해줘.") -> str:
        """
        Kanana Vision 모델로 이미지 분석 (OCR/Description)
        """
        if not self.is_vision:
            return "Error: This is not a vision model."

        if not self.model or not self.processor:
            return "Error: Vision model not loaded."

        try:
            from PIL import Image
            import os

            if not os.path.exists(image_path):
                return f"Error: Image file not found at {image_path}"

            image = Image.open(image_path).convert("RGB")
            
            messages = [
                {"role": "user", "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt}
                ]}
            ]
            
            # Custom processing for Kanana Vision (based on test script)
            # The test script used manual batch construction, but let's try to use the processor's chat template if available,
            # or stick to the manual construction which worked in the test.
            # The test script used:
            # sample = { "image": [image], "conv": [ ... ] }
            # inputs = processor.batch_encode_collate(...)
            
            # Let's use the proven method from the test script for reliability.
            
            sample = {
                "image": [image],
                "conv": [
                    {"role": "user", "content": "<image> " + prompt},
                ]
            }
            
            inputs = self.processor.batch_encode_collate(
                [sample], 
                padding_side="left", 
                add_generation_prompt=True, 
                max_length=4096 # Increased for safety
            )
            
            inputs = {k: v.to(self.device) if isinstance(v, self._torch.Tensor) else v for k, v in inputs.items()}
            
            gen_kwargs = {
                "max_new_tokens": 1024,
                "temperature": 0.0, # Deterministic for OCR
                "do_sample": False,
            }
            
            with self._torch.no_grad():
                outputs = self.model.generate(**inputs, **gen_kwargs)
                
            generated_text = self.processor.tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            
            # Clean up result if needed (the model output might include the prompt or special tokens depending on decoding)
            # The test script output was clean JSON.
            return generated_text

        except Exception as e:
            return f"Vision Analysis Error: {str(e)}"

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

        if not llm.is_vision and llm.tokenizer is None:
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
