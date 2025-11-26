from agent.llm.kanana import LLMManager
import time

def test_integration():
    print("Testing LLMManager Integration...")
    
    # Test 1: Load Vision Model (should use default 8-bit if applicable, or we can specify)
    # Note: Vision model in my implementation uses quantization_config if passed.
    # Let's see if 8-bit works for Vision model too (it should if supported by bitsandbytes for that architecture).
    
    print("\n1. Loading Vision Model...")
    start_time = time.time()
    vision_model = LLMManager.get("vision")
    
    if not vision_model:
        print("❌ Failed to load Vision Model")
        return

    print(f"✅ Vision Model Loaded in {time.time() - start_time:.2f}s")
    
    # Test 2: Analyze Image
    image_path = "./model_vision/examples/waybill.png"
    print(f"\n2. Analyzing Image: {image_path}")
    
    start_time = time.time()
    result = vision_model.analyze_image(image_path)
    print(f"✅ Analysis Result (Time: {time.time() - start_time:.2f}s):")
    print(result[:200] + "..." if len(result) > 200 else result)
    
    # Unload Vision Model to free up VRAM
    print("\nUnloading Vision Model...")
    LLMManager.unload("vision")
    
    # Test 3: Load Text Model (Try 4-bit to ensure it fits after vision unload)
    print("\n3. Loading Text Model (Instruct) with 4-bit...")
    start_time = time.time()
    text_model = LLMManager.get("instruct", quantization="4bit")
    
    if not text_model:
        print("❌ Failed to load Text Model")
        return

    print(f"✅ Text Model Loaded in {time.time() - start_time:.2f}s")
    
    # Test 4: Text Generation
    print("\n4. Generating Text...")
    response = text_model.analyze("안녕하세요")
    print(f"✅ Response: {response}")

if __name__ == "__main__":
    test_integration()
