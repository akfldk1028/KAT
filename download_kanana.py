import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    print("Starting Kanana Model Download...")
    print("Target Model: kakaocorp/kanana-1.5-8b-instruct-2505")
    
    from agent.llm.kanana import KananaLLM
    
    # Initialize 'instruct' model to trigger download
    llm = KananaLLM(model_type="instruct")
    
    print("✅ Download completed successfully!")

except Exception as e:
    print(f"❌ Download failed: {e}")
