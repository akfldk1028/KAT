"""
Agent A (Outgoing) 빠른 테스트 스크립트
발신 메시지의 민감정보(PII) 감지 기능을 테스트합니다.

Usage:
    python quick_test_agent_a.py

Requirements:
    - Backend API running on http://localhost:8002
    - requests library: pip install requests
"""
import requests
import json
from datetime import datetime
import sys
import io
from typing import Dict, List, Any

# UTF-8 출력 설정 (Windows 한글 출력 문제 해결)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# API 엔드포인트
AGENT_A_URL = "http://localhost:8002/api/agents/analyze/outgoing"
METRICS_URL = "http://localhost:3001/api/metrics/agent-a"

# 테스트 케이스 정의
test_cases = [
    # === LOW Risk (일반 대화 & Tier 3 단독) ===
    {
        "case_id": "TEST-A-001",
        "text": "오늘 점심 뭐 먹을까? 칼국수 어때?",
        "expected_risk": "LOW",
        "expected_pii": [],
        "note": "일반 대화 - 민감정보 없음"
    },
    {
        "case_id": "TEST-A-002",
        "text": "홍길동 칼국수 강남구 맛집 진짜 좋더라",
        "expected_risk": "LOW",
        "expected_pii": [],
        "note": "False positive 테스트 - 식당 상호와 지역"
    },
    {
        "case_id": "TEST-A-003",
        "text": "내 이름은 김철수야",
        "expected_risk": "LOW",
        "expected_pii": ["성명"],
        "note": "Tier 3 단독 - 이름만"
    },
    {
        "case_id": "TEST-A-004",
        "text": "나는 1990년생이야",
        "expected_risk": "LOW",
        "expected_pii": ["생년월일"],
        "note": "Tier 3 단독 - 생년만"
    },

    # === MEDIUM Risk (전화번호, 이메일, Tier 3 조합) ===
    {
        "case_id": "TEST-A-005",
        "text": "010-1234-5678로 연락 주세요",
        "expected_risk": "MEDIUM",
        "expected_pii": ["전화번호"],
        "note": "Tier 2 - 전화번호 단독"
    },
    {
        "case_id": "TEST-A-006",
        "text": "내 메일 주소는 hong@example.com이야",
        "expected_risk": "MEDIUM",
        "expected_pii": ["이메일 주소"],
        "note": "Tier 2 - 이메일 단독"
    },
    {
        "case_id": "TEST-A-007",
        "text": "공일공에 일이삼사로 전화해",
        "expected_risk": "MEDIUM",
        "expected_pii": ["전화번호"],
        "note": "자연어 표현 - 전화번호"
    },
    {
        "case_id": "TEST-A-008",
        "text": "홍길동 1990년생 남자 서울시 강남구 살아",
        "expected_risk": "MEDIUM",
        "expected_pii": ["성명", "생년월일", "성별", "주소"],
        "note": "Tier 3 조합 - 4개 항목 결합"
    },
    {
        "case_id": "TEST-A-009",
        "text": "101동 501호에 살아요",
        "expected_risk": "MEDIUM",
        "expected_pii": ["아파트 동/호수"],
        "note": "Tier 2 - 아파트 동/호수"
    },

    # === HIGH Risk (운전면허, 이름+계좌 조합) ===
    {
        "case_id": "TEST-A-010",
        "text": "내 면허번호 12-34-567890-12야",
        "expected_risk": "HIGH",
        "expected_pii": ["운전면허번호"],
        "note": "Tier 2 - 운전면허번호"
    },
    {
        "case_id": "TEST-A-011",
        "text": "홍길동 계좌로 110-123-456789 보내줘",
        "expected_risk": "HIGH",
        "expected_pii": ["성명", "계좌번호"],
        "note": "조합 규칙 - 이름 + 계좌번호 → HIGH"
    },
    {
        "case_id": "TEST-A-012",
        "text": "김철수 카드 1234-5678-9012-3456 사용해",
        "expected_risk": "CRITICAL",
        "expected_pii": ["성명", "신용카드번호"],
        "note": "조합 규칙 - 이름 + 카드번호 → CRITICAL"
    },
    {
        "case_id": "TEST-A-013",
        "text": "주민번호 501041-1****** 확인 부탁해",
        "expected_risk": "HIGH",
        "expected_pii": ["주민등록번호(마스킹)"],
        "note": "마스킹된 주민번호 - HIGH"
    },

    # === CRITICAL Risk (주민번호, 카드번호, 계좌번호) ===
    {
        "case_id": "TEST-A-014",
        "text": "내 주민번호 900101-1234567이야",
        "expected_risk": "CRITICAL",
        "expected_pii": ["주민등록번호"],
        "note": "Tier 1 - 주민등록번호"
    },
    {
        "case_id": "TEST-A-015",
        "text": "카드번호 1234-5678-9012-3456 CVC 123",
        "expected_risk": "CRITICAL",
        "expected_pii": ["신용카드번호", "CVC/CVV"],
        "note": "Tier 1 - 카드번호 + CVC"
    },
    {
        "case_id": "TEST-A-016",
        "text": "110-123-456789 이 계좌로 입금해줘",
        "expected_risk": "CRITICAL",
        "expected_pii": ["계좌번호"],
        "note": "Tier 1 - 계좌번호"
    },
    {
        "case_id": "TEST-A-017",
        "text": "외국인등록번호 501041-5123456",
        "expected_risk": "CRITICAL",
        "expected_pii": ["외국인등록번호"],
        "note": "Tier 1 - 외국인등록번호"
    },
    {
        "case_id": "TEST-A-018",
        "text": "비밀번호는 MyP@ssw0rd123 이야",
        "expected_risk": "CRITICAL",
        "expected_pii": ["ID/비밀번호"],
        "note": "Tier 1 - 비밀번호"
    },
    {
        "case_id": "TEST-A-019",
        "text": "계좌 110-123-456789 카드 1234-5678-9012-3456",
        "expected_risk": "CRITICAL",
        "expected_pii": ["계좌번호", "신용카드번호"],
        "note": "복합 - 계좌 + 카드번호"
    },
    {
        "case_id": "TEST-A-020",
        "text": "주민번호 900101-1234567, 계좌 110-123-456789, 폰 010-1234-5678",
        "expected_risk": "CRITICAL",
        "expected_pii": ["주민등록번호", "계좌번호", "전화번호"],
        "note": "최악의 경우 - 모든 정보 노출"
    }
]


def analyze_message(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent A API를 호출하여 메시지 분석

    Args:
        case: 테스트 케이스 딕셔너리

    Returns:
        분석 결과 딕셔너리 (API 응답 + 검증 결과)
    """
    try:
        response = requests.post(
            AGENT_A_URL,
            json={
                "text": case["text"],
                "sender_id": None,
                "receiver_id": None
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

        # 검증 결과 추가
        risk_match = result["risk_level"] == case["expected_risk"]

        # PII 검증 (간단 버전 - reasons에서 확인)
        detected_pii = []
        for reason in result.get("reasons", []):
            for expected_pii_type in case["expected_pii"]:
                if expected_pii_type in reason:
                    detected_pii.append(expected_pii_type)
                    break

        # 예상 PII 모두 감지되었는지 확인
        pii_match = set(case["expected_pii"]) <= set(detected_pii) if case["expected_pii"] else len(detected_pii) == 0

        return {
            "case_id": case["case_id"],
            "text": case["text"],
            "note": case["note"],
            "expected_risk": case["expected_risk"],
            "actual_risk": result["risk_level"],
            "risk_match": risk_match,
            "expected_pii": case["expected_pii"],
            "detected_pii": detected_pii,
            "pii_match": pii_match,
            "reasons": result.get("reasons", []),
            "recommended_action": result.get("recommended_action", ""),
            "is_secret_recommended": result.get("is_secret_recommended", False),
            "status": "PASS" if (risk_match and pii_match) else "FAIL",
            "error": None
        }

    except Exception as e:
        return {
            "case_id": case["case_id"],
            "text": case["text"],
            "note": case["note"],
            "expected_risk": case["expected_risk"],
            "actual_risk": None,
            "risk_match": False,
            "expected_pii": case["expected_pii"],
            "detected_pii": [],
            "pii_match": False,
            "reasons": [],
            "recommended_action": "",
            "is_secret_recommended": False,
            "status": "ERROR",
            "error": str(e)
        }


def print_result(result: Dict[str, Any], index: int, total: int):
    """테스트 결과 출력"""
    status_symbol = "[PASS]" if result["status"] == "PASS" else "[FAIL]" if result["status"] == "FAIL" else "[ERROR]"

    print(f"\n[{index}/{total}] {result['case_id']} {status_symbol}")
    print(f"  메시지: {result['text']}")
    print(f"  설명: {result['note']}")

    if result["error"]:
        print(f"  에러: {result['error']}")
    else:
        risk_status = "OK" if result["risk_match"] else "FAIL"
        pii_status = "OK" if result["pii_match"] else "FAIL"

        print(f"  위험도: {result['expected_risk']} -> {result['actual_risk']} [{risk_status}]")
        print(f"  예상 PII: {', '.join(result['expected_pii']) if result['expected_pii'] else '없음'}")
        print(f"  감지 PII: {', '.join(result['detected_pii']) if result['detected_pii'] else '없음'} [{pii_status}]")
        print(f"  권장 조치: {result['recommended_action']}")
        print(f"  시크릿 모드: {'권장' if result['is_secret_recommended'] else '불필요'}")

        if result["reasons"]:
            print(f"  이유: {', '.join(result['reasons'])}")


def print_summary(results: List[Dict[str, Any]]):
    """전체 테스트 결과 요약"""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    # 위험도별 통계
    risk_stats = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for r in results:
        if r["actual_risk"]:
            risk_stats[r["actual_risk"]] = risk_stats.get(r["actual_risk"], 0) + 1

    # PII 검출 통계
    total_expected_pii = sum(len(r["expected_pii"]) for r in results)
    total_detected_pii = sum(len(r["detected_pii"]) for r in results)

    print("\n" + "="*80)
    print("테스트 결과 요약")
    print("="*80)
    print(f"총 케이스: {total}")
    print(f"성공: {passed} ({passed/total*100:.1f}%)")
    print(f"실패: {failed} ({failed/total*100:.1f}%)")
    print(f"에러: {errors} ({errors/total*100:.1f}%)")

    print(f"\n위험도 분포:")
    for level, count in risk_stats.items():
        print(f"  {level}: {count}개")

    print(f"\nPII 검출 정확도:")
    print(f"  예상 PII 수: {total_expected_pii}")
    print(f"  검출 PII 수: {total_detected_pii}")
    if total_expected_pii > 0:
        print(f"  검출률: {total_detected_pii/total_expected_pii*100:.1f}%")

    # 실패 케이스 상세
    if failed > 0:
        print(f"\n실패한 케이스:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  {r['case_id']}: {r['expected_risk']} -> {r['actual_risk']}")
                print(f"    메시지: {r['text']}")

    # 에러 케이스 상세
    if errors > 0:
        print(f"\n에러 발생 케이스:")
        for r in results:
            if r["status"] == "ERROR":
                print(f"  {r['case_id']}: {r['error']}")


def send_metrics_to_grafana(results: List[Dict[str, Any]]):
    """Grafana 메트릭 서버로 결과 전송 (선택사항)"""
    try:
        total = len(results)
        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = sum(1 for r in results if r["status"] == "FAIL")
        errors = sum(1 for r in results if r["status"] == "ERROR")

        risk_stats = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for r in results:
            if r["actual_risk"]:
                risk_stats[r["actual_risk"]] = risk_stats.get(r["actual_risk"], 0) + 1

        metrics_data = {
            "agent_a_test_results": {
                "total_cases": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "pass_rate": round(passed / total * 100, 2) if total > 0 else 0,
                "risk_distribution": risk_stats,
                "timestamp": datetime.now().isoformat()
            }
        }

        print("\n" + "="*80)
        print("Grafana 메트릭 전송 중...")
        print("="*80)

        response = requests.post(METRICS_URL, json=metrics_data, timeout=5)
        response.raise_for_status()

        print("[SUCCESS] Grafana에서 확인하세요:")
        print(f"   {METRICS_URL}")
        print("\n메트릭 데이터:")
        print(json.dumps(metrics_data, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"[WARNING] Grafana 전송 실패 (선택사항): {e}")
        print("   테스트 결과는 정상적으로 완료되었습니다.")


def main():
    """메인 테스트 실행 함수"""
    print("\n" + "="*80)
    print("Agent A (Outgoing) 빠른 테스트 시작")
    print("="*80)
    print(f"API 엔드포인트: {AGENT_A_URL}")
    print(f"총 테스트 케이스: {len(test_cases)}")
    print("="*80)

    # 전체 테스트 실행
    results = []
    for i, case in enumerate(test_cases, 1):
        result = analyze_message(case)
        results.append(result)
        print_result(result, i, len(test_cases))

    # 요약 출력
    print_summary(results)

    # Grafana 메트릭 전송 (선택사항)
    try:
        send_metrics_to_grafana(results)
    except Exception as e:
        print(f"\nGrafana 메트릭 전송 건너뜀: {e}")

    # 결과 파일 저장
    output_file = "agent_a_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_date": datetime.now().isoformat(),
            "total_cases": len(results),
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n결과가 {output_file}에 저장되었습니다.")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
