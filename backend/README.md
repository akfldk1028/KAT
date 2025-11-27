
본선 안내	1
카나나 API	1
Kanana-1.5-v-3b	1

카나나 API
Kanana-1.5-v-3b
url: https://kanana-v-3b.a2s-endpoint.kr-central-2.kakaocloud.com/v1/chat/completions
api_key: KC_IS_39DCHwz3U3Og48mP4I8GAiQIH1rzEOiWAHXyk132RcPnsac4fWXJc10JLljl0suE

import base64
from openai import OpenAI

openai_api_key = f"KC_IS_39DCHwz3U3Og48mP4I8GAiQIH1rzEOiWAHXyk132RcPnsac4fWXJc10JLljl0suE"
openai_api_base = "https://kanana-v-3b.a2s-endpoint.kr-central-2.kakaocloud.com/v1"
model = "kanana-1.5-v-3b"

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

# Single-image input inference
def run_single_image() -> None:
    with open('./test.jpeg', "rb") as file:
        image_base64 = base64.b64encode(file.read()).decode("utf-8")
    chat_completion_from_base64 = client.chat.completions.create(
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What's in this image?"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    },
                },
            ],
        }],
        model=model,
        max_completion_tokens=2048,
        extra_body={"add_generation_prompt": True, "stop_token_ids": [128001]},
    )

    result = chat_completion_from_base64.choices[0].message.content
    print("Chat completion output from base64 encoded image:", result)

if __name__ == "__main__":
    run_single_image()

Kanana-2.0


PlayMCP


