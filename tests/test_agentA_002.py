"""
Agent A 테스트 스크립트 - agentA_002.md 테스트 케이스
의미 기반 정규화(Semantic Normalization) 및 _has_suspicious_pattern() 검증
"""
import sys
import json
import re
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.agents.outgoing import OutgoingAgent
from agent.core.pattern_matcher import normalize_korean_numbers, detect_pii


def load_test_cases(filepath: str) -> list:
    """테스트 케이스 파일 로드 (JSON with comments)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # JavaScript 스타일 주석 제거
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'//.*', '', content)

    return json.loads(content)


def test_has_suspicious_pattern():
    """_has_suspicious_pattern() 함수 테스트"""
    print("=" * 60)
    print("테스트 1: _has_suspicious_pattern() 함수 검증")
    print("=" * 60)

    agent = OutgoingAgent()

    test_cases = [
        # 한글 숫자 패턴
        ("구공공일일오 다시 일이삼사오육칠", True, "한글 숫자 연속"),
        ("공일공 일이삼사 오육칠팔", True, "띄어쓴 한글 전화번호"),
        ("M 일이삼사 오육칠팔", True, "여권번호 한글"),

        # 키워드
        ("내 민번 알려줄게", True, "민번 키워드"),
        ("보안카드 번호 불러줄게", True, "보안카드 키워드"),
        ("우울증이 심해", True, "우울증 키워드"),
        ("지문 데이터야", True, "지문 키워드"),
        ("비트코인 지갑 복구", True, "지갑/복구 키워드"),

        # 일반 메시지 (False 예상)
        ("오늘 점심 뭐 먹을까?", False, "일반 대화"),
        ("35,000원이야", False, "단순 가격"),
    ]

    passed = 0
    failed = 0

    for text, expected, desc in test_cases:
        result = agent._has_suspicious_pattern(text)
        status = "[PASS]" if result == expected else "[FAIL]"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} | {desc}")
        print(f"   텍스트: {text}")
        print(f"   예상: {expected}, 결과: {result}")
        print()

    print(f"결과: {passed}/{passed+failed} 통과 ({passed/(passed+failed)*100:.1f}%)")
    return passed, failed


def test_normalize_korean_numbers():
    """한글 숫자 정규화 함수 테스트"""
    print("\n" + "=" * 60)
    print("테스트 2: normalize_korean_numbers() 함수 검증")
    print("=" * 60)

    test_cases = [
        ("구공공일일오", "900115", "주민번호 앞자리"),
        ("일이삼사오육칠", "1234567", "주민번호 뒷자리"),
        ("공일공-일이삼사-오육칠팔", "010-1234-5678", "전화번호"),
        ("M 일이삼사 오육칠팔", "M 1234 5678", "여권번호"),
    ]

    passed = 0
    failed = 0

    for text, expected, desc in test_cases:
        result = normalize_korean_numbers(text)
        status = "[PASS]" if result == expected else "[FAIL]"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} | {desc}")
        print(f"   입력: {text}")
        print(f"   예상: {expected}")
        print(f"   결과: {result}")
        print()

    print(f"결과: {passed}/{passed+failed} 통과 ({passed/(passed+failed)*100:.1f}%)")
    return passed, failed


def test_agentA_002_cases():
    """agentA_002.md 전체 테스트 케이스 검증"""
    print("\n" + "=" * 60)
    print("테스트 3: agentA_002.md 전체 케이스 검증")
    print("=" * 60)

    # 테스트 케이스 로드
    test_file = PROJECT_ROOT / "docs" / "AgentA" / "agentA_002.md"
    if not test_file.exists():
        print(f"[ERROR] 테스트 파일 없음: {test_file}")
        return 0, 1

    test_cases = load_test_cases(str(test_file))
    agent = OutgoingAgent()

    passed = 0
    failed = 0

    for case in test_cases:
        case_id = case["id"]
        principle = case["principle"]
        expected_risk = case["risk_level"]
        messages = case["messages"]
        desc = case["description"]

        # 모든 메시지를 합쳐서 분석 (시계열 맥락 시뮬레이션)
        combined_text = " ".join(messages)

        # _has_suspicious_pattern() 체크
        is_suspicious = agent._has_suspicious_pattern(combined_text)

        # Rule-based 분석 (use_ai=False로 빠른 테스트)
        result = agent.analyze(combined_text, use_ai=False)

        # 예상 위험도 매핑
        expected_map = {
            "critical": ["CRITICAL", "HIGH"],
            "high": ["HIGH", "CRITICAL", "MEDIUM"],
            "medium": ["MEDIUM", "HIGH"],
            "low_to_safe": ["LOW"],
        }

        expected_levels = expected_map.get(expected_risk, ["LOW"])
        actual_risk = result.risk_level.value

        # 결과 판정
        if actual_risk in expected_levels:
            status = "[PASS]"
            passed += 1
        else:
            status = "[FAIL]"
            failed += 1

        print(f"\n{status} | 케이스 #{case_id} [{principle}]")
        print(f"   설명: {desc}")
        print(f"   예상: {expected_risk} → 결과: {actual_risk}")
        print(f"   _has_suspicious_pattern: {is_suspicious}")
        print(f"   이유: {result.reasons[:2] if result.reasons else '없음'}...")

    print(f"\n{'='*60}")
    print(f"최종 결과: {passed}/{passed+failed} 통과 ({passed/(passed+failed)*100:.1f}%)")
    return passed, failed


def test_detect_pii_with_korean():
    """detect_pii가 한글 숫자를 정규화 후 감지하는지 테스트"""
    print("\n" + "=" * 60)
    print("테스트 4: detect_pii() 한글 숫자 정규화 후 감지")
    print("=" * 60)

    test_cases = [
        ("구공공일일오 다시 일이삼사오육칠", "주민번호 한글", True),
        ("공일공 일이삼사 오육칠팔", "전화번호 한글", True),
        ("1234 다시 5678 다시 9012 다시 3456", "카드번호 구분자", True),
    ]

    passed = 0
    failed = 0

    for text, desc, should_detect in test_cases:
        result = detect_pii(text)
        detected = result["count"] > 0

        status = "[PASS]" if detected == should_detect else "[FAIL]"
        if detected == should_detect:
            passed += 1
        else:
            failed += 1

        print(f"{status} | {desc}")
        print(f"   텍스트: {text}")
        print(f"   감지 수: {result['count']}")
        if result["found_pii"]:
            for pii in result["found_pii"][:3]:
                print(f"   - {pii.get('name_ko', pii.get('id'))}: {pii.get('value', 'N/A')}")
        print()

    print(f"결과: {passed}/{passed+failed} 통과 ({passed/(passed+failed)*100:.1f}%)")
    return passed, failed


if __name__ == "__main__":
    print("\n" + "[TEST] Agent A 테스트 시작 (agentA_002.md)")
    print("=" * 60 + "\n")

    total_passed = 0
    total_failed = 0

    # 테스트 실행
    p, f = test_has_suspicious_pattern()
    total_passed += p
    total_failed += f

    p, f = test_normalize_korean_numbers()
    total_passed += p
    total_failed += f

    p, f = test_detect_pii_with_korean()
    total_passed += p
    total_failed += f

    p, f = test_agentA_002_cases()
    total_passed += p
    total_failed += f

    # 최종 결과
    print("\n" + "=" * 60)
    print("[RESULT] 전체 테스트 결과")
    print("=" * 60)
    total = total_passed + total_failed
    rate = total_passed / total * 100 if total > 0 else 0
    print(f"통과: {total_passed}/{total} ({rate:.1f}%)")

    if total_failed > 0:
        print(f"[FAIL] 실패: {total_failed}개")
        sys.exit(1)
    else:
        print("[SUCCESS] 모든 테스트 통과!")
        sys.exit(0)
