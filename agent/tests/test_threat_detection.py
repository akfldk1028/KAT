"""
Agent B (안심 가드) 위협 감지 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent.core.threat_matcher import (
    detect_threats,
    detect_urls,
    match_scam_scenario,
    calculate_threat_score,
    analyze_incoming_message
)


def test_case(name, text, expected_level, expected_scam):
    """단일 테스트 케이스 실행"""
    result = analyze_incoming_message(text)

    actual_level = result["final_assessment"]["threat_level"]
    actual_scam = result["final_assessment"]["is_likely_scam"]

    level_ok = actual_level == expected_level
    scam_ok = actual_scam == expected_scam
    status = 'PASS' if (level_ok and scam_ok) else 'FAIL'

    threats = [t["name_ko"] for t in result["threat_detection"]["found_threats"]]

    return {
        'name': name,
        'text': text,
        'expected_level': expected_level,
        'actual_level': actual_level,
        'expected_scam': expected_scam,
        'actual_scam': actual_scam,
        'threats': threats,
        'score': result["final_assessment"]["threat_score"],
        'warning': result["final_assessment"]["warning_message"],
        'status': status
    }


def run_all_tests():
    """모든 테스트 실행"""
    tests = []

    # 1. 안전한 메시지
    tests.append(test_case('일반 대화', '오늘 저녁 뭐 먹을까?', 'SAFE', False))
    tests.append(test_case('친구 대화', '내일 영화 볼래? 7시에 만나자', 'SAFE', False))
    tests.append(test_case('업무 대화', '회의 자료 보내드렸습니다. 확인 부탁드려요.', 'SAFE', False))

    # 2. 가족 사칭 피싱 (CRITICAL)
    tests.append(test_case(
        '가족사칭-긴급송금',
        '엄마야 폰이 고장나서 새 번호야. 급한데 30만원만 보내줘',
        'CRITICAL', True
    ))
    tests.append(test_case(
        '가족사칭-계좌',
        '아들이야 폰 액정 깨져서 친구폰으로 연락해. 돈 좀 이체해줘 110-123-456789',
        'CRITICAL', True
    ))

    # 3. 기관 사칭 (CRITICAL)
    tests.append(test_case(
        '검찰사칭',
        '서울중앙지검입니다. 귀하의 명의가 범죄에 연루되어 수사 중입니다. 협조 바랍니다.',
        'CRITICAL', True
    ))
    tests.append(test_case(
        '금융감독원사칭',
        '금융감독원입니다. 귀하의 계좌가 해킹되어 동결되었습니다. 본인확인이 필요합니다.',
        'CRITICAL', True
    ))

    # 4. 링크 피싱 (HIGH~CRITICAL)
    tests.append(test_case(
        '단축URL+택배',
        '택배 배송 조회 bit.ly/track123',
        'CRITICAL', True  # 단축URL + 배송 조합 = CRITICAL
    ))
    tests.append(test_case(
        '의심도메인',
        '카카오 보안 업데이트 필요 https://kakao-security.net/update',
        'DANGEROUS', True
    ))

    # 5. 투자 사기
    tests.append(test_case(
        '투자사기',
        '고수익 코인 투자 기회! 원금 100% 보장, 월 30% 수익률!',
        'CRITICAL', True
    ))

    # 6. 대출 유도
    tests.append(test_case(
        '대출유도',
        '저금리 무담보 당일대출 가능! 신용등급 무관 즉시 승인!',
        'DANGEROUS', True
    ))

    # 7. 정보 탈취
    tests.append(test_case(
        '인증정보요청',
        '계좌 보안을 위해 비밀번호와 OTP를 알려주세요.',
        'CRITICAL', True
    ))
    tests.append(test_case(
        '신분증요청',
        '본인확인을 위해 주민등록증 사진을 보내주세요.',
        'CRITICAL', True
    ))

    # 8. 심리적 압박
    tests.append(test_case(
        '시간압박',
        '오늘까지 입금하지 않으면 법적 조치하겠습니다. 지금 당장 처리하세요.',
        'SUSPICIOUS', False
    ))
    tests.append(test_case(
        '당첨사기',
        '축하합니다! 이벤트 당첨되셨습니다. 경품 수령을 위해 계좌번호를 알려주세요.',
        'CRITICAL', True  # 계좌번호 요청 포함 = CRITICAL
    ))

    # 9. 복합 패턴 (매우 위험)
    tests.append(test_case(
        '검찰+공포+링크',
        '검찰입니다. 귀하 명의로 범죄가 발생했습니다. 체포를 피하려면 bit.ly/safe-account 접속하세요.',
        'CRITICAL', True
    ))

    return tests


def main():
    print("=" * 70)
    print("    Agent B (안심 가드) 위협 감지 테스트")
    print("=" * 70)
    print()

    # 테스트 실행
    tests = run_all_tests()

    # 결과 출력
    for t in tests:
        status_icon = '[PASS]' if t['status'] == 'PASS' else '[FAIL]'
        print(f"{status_icon} {t['name']}")
        print(f"    입력: {t['text'][:50]}...")
        print(f"    레벨: {t['actual_level']} (예상: {t['expected_level']})")
        print(f"    사기: {'O' if t['actual_scam'] else 'X'} (예상: {'O' if t['expected_scam'] else 'X'})")
        print(f"    점수: {t['score']}")
        if t['threats']:
            print(f"    감지: {', '.join(t['threats'][:3])}")
        print()

    # 요약
    pass_count = sum(1 for t in tests if t['status'] == 'PASS')
    fail_count = sum(1 for t in tests if t['status'] == 'FAIL')

    print("=" * 70)
    print(f"결과: {pass_count}/{len(tests)} 통과 ({pass_count/len(tests)*100:.1f}%)")
    print("=" * 70)

    # 실패 케이스 상세
    if fail_count > 0:
        print()
        print("실패 케이스:")
        for t in tests:
            if t['status'] == 'FAIL':
                print(f"  - {t['name']}: 예상 {t['expected_level']}/{t['expected_scam']} vs 실제 {t['actual_level']}/{t['actual_scam']}")


if __name__ == "__main__":
    main()
