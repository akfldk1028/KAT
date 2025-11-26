import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import time

# Use local model path
MODEL_PATH = "./model"

print(f"Loading model from {MODEL_PATH}...")
start_load = time.time()

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4"
)

try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        quantization_config=quantization_config if device == "cuda" else None,
        torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        device_map="auto",
        trust_remote_code=True,
    )
except Exception as e:
    print(f"❌ Error loading model: {e}")
    exit(1)

print(f"✅ Model loaded! (Time: {time.time() - start_load:.2f}s)")

# Test prompt
messages = [
    {"role": "user", "content": "안녕하세요! 카나나에 대해 소개해줘."}
]

input_text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)

inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

# Generation config
gen_kwargs = {
    "max_new_tokens": 512,
    "temperature": 0.7,
    "top_p": 0.9,
    "do_sample": True,
    "eos_token_id": tokenizer.eos_token_id,
    "pad_token_id": tokenizer.pad_token_id,
}

print("Generating response...")
start_gen = time.time()

with torch.no_grad():
    outputs = model.generate(**inputs, **gen_kwargs)

end_gen = time.time()

generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
response = generated_text[len(input_text):] # Naive strip, might need adjustment based on template

print("\n--- Result ---")
print(generated_text)
print("--------------")
print(f"⏱️ Generation Time: {end_gen - start_gen:.2f}s")
print(f"⏱️ Total Time: {end_gen - start_load:.2f}s")
