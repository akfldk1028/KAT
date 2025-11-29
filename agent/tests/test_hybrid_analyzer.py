"""
Hybrid Analyzer Test - Rule + LLM 통합 분석기 테스트
TestData CSV를 사용하여 감지율 비교
"""
import csv
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent.core.pattern_matcher import detect_pii, calculate_risk, get_risk_action
from agent.core.hybrid_analyzer import hybrid_analyze


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


def rule_based_analyze(text: str) -> dict:
    """Rule-based 분석"""
    pii_result = detect_pii(text)
    risk_result = calculate_risk(pii_result["found_pii"])
    return {
        "pii_count": pii_result["count"],
        "risk_level": risk_result["final_risk"],
        "found_pii": pii_result["found_pii"]
    }


def test_comparison():
    """Rule-based vs Hybrid 비교 테스트"""
    print("=" * 70)
    print("      Hybrid Analyzer Test - Rule vs Hybrid 비교")
    print("=" * 70)
    print()

    test_cases = load_csv_testdata()

    # 결과 집계
    rule_results = {"total": 0, "detected": 0, "by_category": {}, "by_risk": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}}
    hybrid_results = {"total": 0, "detected": 0, "by_category": {}, "by_risk": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}}

    # 특정 케이스 상세 비교 (처음 5개 + 문맥은닉 케이스)
    detailed_indices = [0, 1, 2, 3, 4]  # 처음 5개
    context_hidden_indices = []  # 문맥은닉 케이스 인덱스

    for idx, case in enumerate(test_cases):
        if "문맥은닉" in case["category"]:
            context_hidden_indices.append(idx)

    detailed_indices.extend(context_hidden_indices)

    print("[1/3] Rule-based 분석 중...")
    for idx, case in enumerate(test_cases):
        rule_results["total"] += 1

        result = rule_based_analyze(case["text"])

        if result["pii_count"] > 0:
            rule_results["detected"] += 1

        rule_results["by_risk"][result["risk_level"]] += 1

        cat = case["category"]
        if cat not in rule_results["by_category"]:
            rule_results["by_category"][cat] = {"total": 0, "detected": 0}
        rule_results["by_category"][cat]["total"] += 1
        if result["pii_count"] > 0:
            rule_results["by_category"][cat]["detected"] += 1

    print("[2/3] Hybrid 분석 중 (LLM 포함)...")
    print("     (LLM API 호출로 시간이 걸릴 수 있습니다)")
    print()

    for idx, case in enumerate(test_cases):
        hybrid_results["total"] += 1

        # Hybrid 분석 (LLM 사용)
        result = hybrid_analyze(case["text"], use_llm=True)

        pii_count = result.get("total_pii_count", len(result.get("found_pii", [])))
        risk_level = result.get("risk_level", "LOW")

        if pii_count > 0:
            hybrid_results["detected"] += 1

        hybrid_results["by_risk"][risk_level] += 1

        cat = case["category"]
        if cat not in hybrid_results["by_category"]:
            hybrid_results["by_category"][cat] = {"total": 0, "detected": 0}
        hybrid_results["by_category"][cat]["total"] += 1
        if pii_count > 0:
            hybrid_results["by_category"][cat]["detected"] += 1

        # 상세 출력
        if idx in detailed_indices:
            print(f"[{idx+1:02d}] {case['category']} - {case['item']}")
            print(f"     입력: {case['text'][:50]}...")

            # Rule-based 결과
            rule_res = rule_based_analyze(case["text"])
            print(f"     [Rule] PII: {rule_res['pii_count']}개, 위험도: {rule_res['risk_level']}")

            # Hybrid 결과
            print(f"     [Hybrid] PII: {pii_count}개, 위험도: {risk_level}")
            if result.get("llm_reasoning"):
                print(f"     [LLM 판단] {result['llm_reasoning'][:60]}...")
            print()

        # 진행률 표시
        if (idx + 1) % 10 == 0:
            print(f"     진행: {idx + 1}/{len(test_cases)}건 완료")

    # 결과 비교
    print()
    print("=" * 70)
    print("      결과 비교")
    print("=" * 70)
    print()

    rule_rate = rule_results["detected"] / rule_results["total"] * 100
    hybrid_rate = hybrid_results["detected"] / hybrid_results["total"] * 100
    improvement = hybrid_rate - rule_rate

    print(f"{'항목':<20} {'Rule-based':<15} {'Hybrid':<15} {'개선':<10}")
    print("-" * 60)
    print(f"{'총 테스트':<20} {rule_results['total']:<15} {hybrid_results['total']:<15}")
    print(f"{'PII 감지':<20} {rule_results['detected']:<15} {hybrid_results['detected']:<15} +{hybrid_results['detected'] - rule_results['detected']}")
    print(f"{'감지율':<20} {rule_rate:.1f}%{'':<10} {hybrid_rate:.1f}%{'':<10} +{improvement:.1f}%")
    print()

    print("위험도별 분포:")
    print(f"{'위험도':<12} {'Rule-based':<15} {'Hybrid':<15}")
    print("-" * 40)
    for risk in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        print(f"{risk:<12} {rule_results['by_risk'][risk]:<15} {hybrid_results['by_risk'][risk]:<15}")
    print()

    print("카테고리별 감지율:")
    print(f"{'카테고리':<20} {'Rule-based':<15} {'Hybrid':<15}")
    print("-" * 50)
    for cat in rule_results["by_category"]:
        rule_cat = rule_results["by_category"][cat]
        hybrid_cat = hybrid_results["by_category"].get(cat, {"total": 0, "detected": 0})

        rule_cat_rate = rule_cat["detected"] / rule_cat["total"] * 100 if rule_cat["total"] > 0 else 0
        hybrid_cat_rate = hybrid_cat["detected"] / hybrid_cat["total"] * 100 if hybrid_cat["total"] > 0 else 0

        print(f"{cat:<20} {rule_cat_rate:.0f}%{'':<12} {hybrid_cat_rate:.0f}%")

    print()
    print("=" * 70)
    print("      테스트 완료")
    print("=" * 70)

    return {
        "rule": rule_results,
        "hybrid": hybrid_results,
        "improvement": improvement
    }


def test_specific_cases():
    """특정 케이스 상세 테스트 (문맥은닉, 노이즈 등)"""
    print()
    print("=" * 70)
    print("      특정 케이스 상세 분석")
    print("=" * 70)
    print()

    # 문맥은닉/노이즈 케이스
    hard_cases = [
        ("문맥은닉/구어체", "아니 제가 95년 3월생인데, 서울시 강남구 역삼동... 산다고요."),
        ("문맥은닉/띄어쓰기무시", "비밀번호는dkagh1234!이고아이디는user01입니다"),
        ("노이즈/이메일회피", "아이디는 myname [at] gmail [dot] com 입니다."),
        ("기타/OCR오류", "여권번호 M1234S678 (5를 S로 오인식), 이름 ㄱㅣㅁㅊㅓㄹㅅㅜ"),
        ("기타/서류형태", "성명:최인재, 주민:921010-1******, 주소:수원시 영통구..."),
    ]

    for case_name, text in hard_cases:
        print(f"[{case_name}]")
        print(f"입력: {text}")
        print()

        # Rule-based
        rule_res = rule_based_analyze(text)
        print(f"  [Rule-based]")
        print(f"    PII: {rule_res['pii_count']}개, 위험도: {rule_res['risk_level']}")
        if rule_res["found_pii"]:
            pii_names = [p["name_ko"] for p in rule_res["found_pii"]]
            print(f"    감지: {', '.join(set(pii_names))}")

        # Hybrid
        hybrid_res = hybrid_analyze(text, use_llm=True)
        pii_count = hybrid_res.get("total_pii_count", len(hybrid_res.get("found_pii", [])))
        print(f"  [Hybrid]")
        print(f"    PII: {pii_count}개, 위험도: {hybrid_res['risk_level']}")
        if hybrid_res.get("found_pii"):
            pii_names = [p.get("name_ko", p.get("type_ko", "")) for p in hybrid_res["found_pii"]]
            print(f"    감지: {', '.join(set(filter(None, pii_names)))}")
        if hybrid_res.get("llm_reasoning"):
            print(f"    [LLM 판단] {hybrid_res['llm_reasoning']}")

        print()
        print("-" * 50)
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Hybrid Analyzer Test")
    parser.add_argument("--full", action="store_true", help="전체 CSV 테스트 (시간 소요)")
    parser.add_argument("--specific", action="store_true", help="특정 케이스 상세 테스트")
    args = parser.parse_args()

    if args.full:
        test_comparison()
    elif args.specific:
        test_specific_cases()
    else:
        # 기본: 특정 케이스만
        test_specific_cases()
