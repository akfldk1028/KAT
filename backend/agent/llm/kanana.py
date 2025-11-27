"""
Kanana LLM Manager
Vision 및 Instruct 모델 관리
- Vision: API 호출 (OCR용)
- Instruct: 로컬 모델 (텍스트 분석용)
"""

import os
import base64
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# .env 파일 로드
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# 로컬 모델 경로
LOCAL_MODEL_PATH = Path(__file__).parent.parent.parent.parent / "model"


class KananaVision:
    """Kanana Vision 모델 클라이언트 (OCR용)"""

    def __init__(self):
        self.api_key = os.getenv("KANANA_VISION_API_KEY")
        self.base_url = os.getenv("KANANA_VISION_BASE_URL")
        self.model = os.getenv("KANANA_VISION_MODEL", "kanana-1.5-v-3b")

        if not self.api_key or not self.base_url:
            raise ValueError("KANANA_VISION_API_KEY and KANANA_VISION_BASE_URL must be set in .env")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def analyze_image(self, image_path: str, prompt: str = None) -> str:
        """
        이미지에서 텍스트 추출 (OCR)

        Args:
            image_path: 이미지 파일 경로
            prompt: 커스텀 프롬프트 (기본: OCR 프롬프트)

        Returns:
            추출된 텍스트
        """
        if prompt is None:
            prompt = """이 이미지에서 모든 텍스트를 추출해주세요.
텍스트가 있다면 그대로 출력하고, 텍스트가 없다면 "텍스트 없음"이라고 답해주세요.
개인정보(계좌번호, 주민번호, 전화번호, 주소 등)가 보이면 그것도 포함해서 추출해주세요."""

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
            model=self.model,
            max_completion_tokens=2048,
            extra_body={"add_generation_prompt": True, "stop_token_ids": [128001]},
        )

        return response.choices[0].message.content


class KananaInstruct:
    """Kanana Instruct 로컬 모델 (텍스트 분석용)"""

    _model = None
    _tokenizer = None

    def __init__(self):
        self.model_path = str(LOCAL_MODEL_PATH)
        self._load_model()

    def _load_model(self):
        """로컬 모델 로드 (싱글톤)"""
        if KananaInstruct._model is None:
            print(f"Loading local model from {self.model_path}...")
            try:
                KananaInstruct._tokenizer = AutoTokenizer.from_pretrained(
                    self.model_path,
                    trust_remote_code=True
                )
                KananaInstruct._model = AutoModelForCausalLM.from_pretrained(
                    self.model_path,
                    torch_dtype=torch.bfloat16,
                    device_map="auto",
                    trust_remote_code=True
                )
                print("Local model loaded successfully!")
            except Exception as e:
                print(f"Failed to load local model: {e}")
                KananaInstruct._model = None
                KananaInstruct._tokenizer = None

    def is_available(self) -> bool:
        """Instruct 모델 사용 가능 여부"""
        return KananaInstruct._model is not None and KananaInstruct._tokenizer is not None

    def analyze_text(self, text: str, analysis_type: str = "pii") -> str:
        """
        텍스트 분석 (로컬 LLM)

        Args:
            text: 분석할 텍스트
            analysis_type: 분석 유형 ("pii" 또는 "threat")

        Returns:
            분석 결과
        """
        if not self.is_available():
            raise ValueError("Kanana Instruct model is not available")

        if analysis_type == "pii":
            system_prompt = """당신은 개인정보 보호 전문가입니다.
주어진 텍스트에서 개인정보를 찾아 분석해주세요.

다음 형식으로 답변해주세요:
- 위험수준: [safe/low/medium/high/critical]
- 발견된 개인정보: [목록]
- 권장 조치: [설명]
- 비밀채팅 권장: [예/아니오]"""
        else:
            system_prompt = """당신은 보안 위협 분석 전문가입니다.
주어진 메시지에서 피싱, 스미싱, 사기 패턴을 찾아 분석해주세요.

다음 형식으로 답변해주세요:
- 위험수준: [safe/low/medium/high/critical]
- 발견된 위협: [목록]
- 권장 조치: [설명]"""

        # 프롬프트 구성
        prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n다음 텍스트를 분석해주세요:\n\n{text}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"

        # 토크나이즈
        inputs = KananaInstruct._tokenizer(prompt, return_tensors="pt").to(KananaInstruct._model.device)

        # 생성
        with torch.no_grad():
            outputs = KananaInstruct._model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                pad_token_id=KananaInstruct._tokenizer.pad_token_id,
                eos_token_id=KananaInstruct._tokenizer.eos_token_id,
            )

        # 디코딩
        response = KananaInstruct._tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        return response.strip()


class LLMManager:
    """LLM 인스턴스 관리자 (싱글톤 패턴)"""

    _instances: Dict[str, Any] = {}

    @classmethod
    def get(cls, model_type: str) -> Optional[Any]:
        """
        LLM 인스턴스 가져오기

        Args:
            model_type: "vision" 또는 "instruct"

        Returns:
            해당 모델 클라이언트 인스턴스
        """
        if model_type not in cls._instances:
            try:
                if model_type == "vision":
                    cls._instances[model_type] = KananaVision()
                elif model_type == "instruct":
                    instance = KananaInstruct()
                    if instance.is_available():
                        cls._instances[model_type] = instance
                    else:
                        return None
                else:
                    return None
            except Exception as e:
                print(f"Failed to initialize {model_type} model: {e}")
                return None

        return cls._instances.get(model_type)

    @classmethod
    def clear(cls):
        """모든 인스턴스 초기화"""
        cls._instances.clear()
