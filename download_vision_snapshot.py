import sys
import os
from huggingface_hub import snapshot_download

try:
    print("Starting Kanana Vision Model Snapshot Download...")
    model_id = "kakaocorp/kanana-1.5-v-3b-instruct"
    
    # Download to default cache
    snapshot_download(repo_id=model_id)
    
    print("✅ Snapshot download completed successfully!")

except Exception as e:
    print(f"❌ Download failed: {e}")
