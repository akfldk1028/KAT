"""
MCP 도구 테스트 - TestData 폴더 활용
CSV 텍스트 데이터와 이미지 데이터로 분석 도구 검증
"""
import csv
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent.core.pattern_matcher import (
    detect_pii, calculate_risk, get_risk_action,
    detect_document_type, get_pii_patterns
)


def load_csv_testdata():
    """CSV 테스트 데이터 로드"""
    csv_path = project_root / "TestData" / "Text" / "개인정보 데이터 샘플문장 생성 - 개인정보 생성 데이터.csv"

    test_cases = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            test_cases.append({
                "category": row["대분류"],
                "item": row["세부 항목"],
                "text": row["테스트 데이터 (문장/내용)"],
                "note": row.get("비고", "")
            })
    return test_cases


def analyze_full(text: str) -> dict:
    """전체 분석 파이프라인"""
    pii_result = detect_pii(text)
    risk_result = calculate_risk(pii_result["found_pii"])
    action = get_risk_action(risk_result["final_risk"])

    return {
        "pii_scan": pii_result,
        "risk_evaluation": risk_result,
        "recommended_action": action
    }


def test_text_analysis():
    """CSV 텍스트 데이터로 분석 테스트"""
    print("=" * 60)
    print("MCP 텍스트 분석 테스트 (CSV 데이터)")
    print("=" * 60)
    print()

    test_cases = load_csv_testdata()

    results = {
        "total": 0,
        "detected": 0,
        "by_category": {},
        "by_risk": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    }

    for case in test_cases:
        results["total"] += 1

        # 분석 실행
        analysis = analyze_full(case["text"])
        pii_count = analysis["pii_scan"]["count"]
        risk_level = analysis["risk_evaluation"]["final_risk"]

        if pii_count > 0:
            results["detected"] += 1

        results["by_risk"][risk_level] += 1

        # 카테고리별 집계
        cat = case["category"]
        if cat not in results["by_category"]:
            results["by_category"][cat] = {"total": 0, "detected": 0}
        results["by_category"][cat]["total"] += 1
        if pii_count > 0:
            results["by_category"][cat]["detected"] += 1

        # 상세 출력 (처음 5개 + 마지막 2개만)
        if results["total"] <= 5 or results["total"] > len(test_cases) - 2:
            print(f"[{results['total']:02d}] {case['category']} - {case['item']}")
            print(f"     입력: {case['text'][:50]}...")
            print(f"     결과: PII {pii_count}개 | 위험도: {risk_level} | {analysis['recommended_action']}")
            if analysis["pii_scan"]["found_pii"]:
                pii_names = [p["name_ko"] for p in analysis["pii_scan"]["found_pii"]]
                print(f"     감지: {', '.join(set(pii_names))}")
            print()
        elif results["total"] == 6:
            print("     ... (중간 생략) ...")
            print()

    # 요약
    print("=" * 60)
    print("텍스트 분석 결과 요약")
    print("=" * 60)
    print(f"총 테스트: {results['total']}건")
    print(f"PII 감지: {results['detected']}건 ({results['detected']/results['total']*100:.1f}%)")
    print()
    print("위험도별 분포:")
    for risk, count in results["by_risk"].items():
        bar = "#" * (count * 2)
        print(f"  {risk:10s}: {count:2d}건 {bar}")
    print()
    print("카테고리별 감지율:")
    for cat, data in results["by_category"].items():
        rate = data["detected"] / data["total"] * 100 if data["total"] > 0 else 0
        print(f"  {cat}: {data['detected']}/{data['total']} ({rate:.0f}%)")

    return results


def test_document_detection():
    """문서 유형 감지 테스트"""
    print()
    print("=" * 60)
    print("문서 유형 감지 테스트")
    print("=" * 60)
    print()

    # 각 문서 유형에 대한 샘플 OCR 텍스트
    sample_ocr_texts = [
        ("주민등록증", "주민등록증 홍길동 900101-1234567 서울특별시 강남구"),
        ("운전면허증", "운전면허증 제1종보통 11-12-345678-90 면허증 번호"),
        ("여권", "PASSPORT 대한민국 M12345678 HONG GIL DONG"),
        ("가족관계증명서", "가족관계증명서 등록기준지 본인 배우자 자녀"),
        ("주민등록등본", "주민등록 등본 세대주 세대원 주소지 전입일자"),
    ]

    for doc_name, ocr_text in sample_ocr_texts:
        result = detect_document_type(ocr_text)
        status = "[O]" if result["document_type"] else "[X]"
        print(f"{status} {doc_name}: {result.get('name_ko', 'N/A')} (신뢰도: {result['confidence']})")

    print()


def main():
    """메인 테스트 실행"""
    print()
    print("=" * 60)
    print("          DualGuard MCP Tools Test")
    print("=" * 60)
    print()

    # 1. 텍스트 분석 테스트
    text_results = test_text_analysis()

    # 2. 문서 유형 감지 테스트
    test_document_detection()

    # 3. 특정 케이스 상세 테스트
    print("=" * 60)
    print("특정 케이스 상세 분석")
    print("=" * 60)
    print()

    detailed_cases = [
        "주민번호 900101-1234567 입니다",
        "이름은 이영희, 주민번호 880505-2234567, 폰번호 010-9876-5432입니다.",
        "신한카드 5361-1234-5678-1234 (CVC 123) 실패시 농협 302-1234-5678-91로 이체.",
    ]

    for text in detailed_cases:
        print(f"입력: {text}")
        result = analyze_full(text)

        print(f"  PII 스캔:")
        for pii in result["pii_scan"]["found_pii"]:
            print(f"    - {pii['name_ko']}: {pii['value']} ({pii['risk_level']})")

        print(f"  위험도 평가:")
        print(f"    - 기본: {result['risk_evaluation']['base_risk']}")
        print(f"    - 최종: {result['risk_evaluation']['final_risk']}")
        if result['risk_evaluation']['escalation_reason']:
            print(f"    - 상향 이유: {result['risk_evaluation']['escalation_reason']}")

        print(f"  권장 조치: {result['recommended_action']}")
        print()

    print("=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
