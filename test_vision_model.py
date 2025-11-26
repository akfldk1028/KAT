from PIL import Image
import torch
from transformers import AutoModelForVision2Seq, AutoProcessor
import os

import time

# Use local model path
MODEL = "./model_vision"

print(f"Loading model from {MODEL}...")
start_load = time.time()

# Load the model on the available device(s)
# Note: Added _attn_implementation="eager" to be safe, though modeling.py is patched.
# Using device_map="auto" as requested, but if it fails with offload error, we might need to change it.
try:
    model = AutoModelForVision2Seq.from_pretrained(
        MODEL,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        _attn_implementation="eager" 
    )
except ValueError as e:
    if "offload" in str(e):
        print("⚠️ device_map='auto' failed (offload error). Falling back to manual device placement.")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = AutoModelForVision2Seq.from_pretrained(
            MODEL,
            torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
            trust_remote_code=True,
            _attn_implementation="eager"
        ).to(device)
    else:
        raise e

model.eval()
print(f"✅ Model loaded! (Time: {time.time() - start_load:.2f}s)")

# Load processor
processor = AutoProcessor.from_pretrained(MODEL, trust_remote_code=True)
print("✅ Processor loaded!")

# Prepare input batch
batch = []
# Correct path to the example image
image_path = "./model_vision/examples/waybill.png"

if not os.path.exists(image_path):
    print(f"❌ Image not found at {image_path}")
    exit(1)

print(f"Processing image: {image_path}")

for _ in range(1):  # dummy loop to demonstrate batch processing
    image_files = [
        image_path
    ]

    sample = {
        "image": [Image.open(image_file_path).convert("RGB") for image_file_path in image_files],
        "conv": [
            {"role": "user", "content": " ".join(["<image>"] * len(image_files))},
            {"role": "user", "content": "사진에서 보내는 사람과 받는 사람 정보를 json 형태로 정리해줘."},
        ]
    }

    batch.append(sample)
    
inputs = processor.batch_encode_collate(
    batch, padding_side="left", add_generation_prompt=True, max_length=8192
)
inputs = {k: v.to(model.device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

# Set the generation config
gen_kwargs = {
    "max_new_tokens": 2048,
    "temperature": 0,
    "top_p": 1.0,
    "num_beams": 1,
    "do_sample": False,
}

print("Generating response...")
start_gen = time.time()
# Generate text
gens = model.generate(
    **inputs,
    **gen_kwargs,
)
end_gen = time.time()
text_outputs = processor.tokenizer.batch_decode(gens, skip_special_tokens=True)
print("\n--- Result ---")
print(text_outputs)
print("--------------")
print(f"⏱️ Generation Time: {end_gen - start_gen:.2f}s")
print(f"⏱️ Total Time: {end_gen - start_load:.2f}s")

