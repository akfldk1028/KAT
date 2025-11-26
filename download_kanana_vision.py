import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    print("Starting Kanana Vision Model Download...")
    print("Target Model: kakaocorp/kanana-1.5-v-3b-instruct")
    
    from agent.llm.kanana import KananaLLM
    
    # Initialize 'vision' model to trigger download
    # This will try to load from ./model_vision, fail (because it's empty),
    # but the logic in KananaLLM needs to be slightly adjusted to download if local path doesn't exist?
    # WAIT: KananaLLM currently points to "./model_vision". 
    # If I pass the HF ID directly here for download purposes, it's better.
    # But KananaLLM init logic uses self.model_id which is hardcoded in __init__.
    
    # Let's temporarily override the model_id in the instance or just use the HF ID in the script
    # to download it to cache first, then move it.
    # Actually, AutoModel...from_pretrained(local_path) will fail if not found.
    # It won't download from HF if I give it a local path that doesn't exist.
    
    # So I should use the HF ID in this script to download to cache.
    
    from transformers import AutoModelForCausalLM, AutoTokenizer
    
    model_id = "kakaocorp/kanana-1.5-v-3b-instruct"
    print(f"Downloading {model_id} to cache...")
    
    AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
    
    print("✅ Download completed successfully!")

except Exception as e:
    print(f"❌ Download failed: {e}")
