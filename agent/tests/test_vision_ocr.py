"""
Vision OCR Test - TestData Image folder
"""
import sys
from pathlib import Path

# Project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent.llm.kanana import LLMManager
from agent.core.pattern_matcher import detect_pii, calculate_risk, get_risk_action, detect_document_type


def analyze_full(text: str) -> dict:
    """Full analysis pipeline"""
    pii_result = detect_pii(text)
    risk_result = calculate_risk(pii_result["found_pii"])
    action = get_risk_action(risk_result["final_risk"])
    return {
        "pii_scan": pii_result,
        "risk_evaluation": risk_result,
        "recommended_action": action
    }


def test_vision_ocr():
    """Test Vision OCR with TestData images"""
    print("=" * 60)
    print("Vision OCR Test")
    print("=" * 60)
    print()

    # Get Vision model
    print("[1/3] Loading Vision model...")
    vision = LLMManager.get("vision")

    if not vision or not vision.is_ready():
        print("[ERROR] Vision model not ready. Check API configuration.")
        return

    print("[OK] Vision model ready")
    print()

    # Image files
    image_dir = project_root / "TestData" / "Image"
    if not image_dir.exists():
        print(f"[ERROR] Image directory not found: {image_dir}")
        return

    # Select test images (1 of each type)
    test_images = [
        image_dir / "주민등록증001.png",
        image_dir / "운전면허증001.png",
        image_dir / "여권001.png",
    ]

    # Filter existing files
    test_images = [img for img in test_images if img.exists()]

    print(f"[2/3] Testing {len(test_images)} images...")
    print()

    results = []

    for img_path in test_images:
        print(f"Image: {img_path.name}")
        print("-" * 40)

        try:
            # OCR
            ocr_text = vision.analyze_image(str(img_path))
            print(f"  OCR Result: {ocr_text[:100]}..." if len(ocr_text) > 100 else f"  OCR Result: {ocr_text}")

            # Document type detection
            doc_type = detect_document_type(ocr_text)
            print(f"  Document Type: {doc_type.get('name_ko', 'Unknown')} ({doc_type['confidence']})")

            # PII Analysis
            analysis = analyze_full(ocr_text)
            pii_count = analysis["pii_scan"]["count"]
            risk_level = analysis["risk_evaluation"]["final_risk"]

            print(f"  PII Count: {pii_count}")
            print(f"  Risk Level: {risk_level}")
            print(f"  Action: {analysis['recommended_action']}")

            if analysis["pii_scan"]["found_pii"]:
                pii_names = list(set(p["name_ko"] for p in analysis["pii_scan"]["found_pii"]))
                print(f"  Detected: {', '.join(pii_names)}")

            results.append({
                "image": img_path.name,
                "doc_type": doc_type.get("name_ko"),
                "pii_count": pii_count,
                "risk_level": risk_level,
                "success": True
            })

        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({
                "image": img_path.name,
                "success": False,
                "error": str(e)
            })

        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    success_count = sum(1 for r in results if r.get("success"))
    print(f"Total: {len(results)}, Success: {success_count}")

    for r in results:
        if r.get("success"):
            print(f"  [O] {r['image']}: {r.get('doc_type', 'N/A')} - {r.get('risk_level', 'N/A')}")
        else:
            print(f"  [X] {r['image']}: {r.get('error', 'Unknown error')}")


if __name__ == "__main__":
    test_vision_ocr()
