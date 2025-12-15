"""
TheCheat API 통합 테스트 스크립트

테스트 데이터:
- 전화번호: 01044440000
- 계좌번호: 12010123456

실행 방법:
1. .env 파일에 THECHEAT_API_KEY 설정
2. python test_thecheat_integration.py
"""
import sys
from pathlib import Path

# agent 모듈 경로 추가
agent_path = Path(__file__).parent / "agent"
sys.path.insert(0, str(agent_path))

from dotenv import load_dotenv
load_dotenv()

from core.scam_checker import check_scam_in_message

def test_phone_check():
    """전화번호 조회 테스트"""
    print("\n" + "="*50)
    print("테스트 1: 전화번호 조회 (01044440000)")
    print("="*50)

    text = "이 번호로 연락주세요: 010-4444-0000"
    result = check_scam_in_message(text)

    print(f"\n[OK] 신고 여부: {result['has_reported_identifier']}")
    print(f"[PHONE] 추출된 전화번호: {result['extracted_identifiers']['phones']}")

    if result['reported_phones']:
        for phone in result['reported_phones']:
            print(f"\n[ALERT] 신고 이력 발견!")
            print(f"   - 전화번호: {phone['phone_number']}")
            print(f"   - 출처: {phone.get('source', 'MockDB')}")
            print(f"   - 상태: {phone['status_name_ko']}")
            print(f"   - 신고 유형: {phone['report_type']}")
            if phone.get('details'):
                print(f"   - 상세 내용: {phone['details']}")
    else:
        print("\n[OK] 신고 이력 없음")

    print(f"\n[WARN] 최대 위험 점수: {result['max_risk_score']}")
    print(f"[ACTION] 권장 조치: {result['recommended_action']}")
    print(f"[SOURCE] 조회 소스: {result.get('sources', [])}")

def test_account_check():
    """계좌번호 조회 테스트"""
    print("\n" + "="*50)
    print("테스트 2: 계좌번호 조회 (12010123456)")
    print("="*50)

    text = "이 계좌로 송금하세요: 1201-01-23456"
    result = check_scam_in_message(text)

    print(f"\n[OK] 신고 여부: {result['has_reported_identifier']}")
    print(f"[ACCOUNT] 추출된 계좌번호: {result['extracted_identifiers']['accounts']}")

    if result['reported_accounts']:
        for account in result['reported_accounts']:
            print(f"\n[ALERT] 신고 이력 발견!")
            print(f"   - 계좌번호: {account['account_number']}")
            print(f"   - 출처: {account.get('source', 'MockDB')}")
            print(f"   - 은행: {account['bank']}")
            print(f"   - 상태: {account['status_name_ko']}")
            print(f"   - 신고 유형: {account['report_type']}")
            if account.get('details'):
                print(f"   - 상세 내용: {account['details']}")
    else:
        print("\n[OK] 신고 이력 없음")

    print(f"\n[WARN] 최대 위험 점수: {result['max_risk_score']}")
    print(f"[ACTION] 권장 조치: {result['recommended_action']}")
    print(f"[SOURCE] 조회 소스: {result.get('sources', [])}")

def test_combined():
    """전화번호 + 계좌번호 동시 조회 테스트"""
    print("\n" + "="*50)
    print("테스트 3: 전화번호 + 계좌번호 동시 조회")
    print("="*50)

    text = """
    긴급! 아들이 사고났어요.
    010-4444-0000으로 연락주시고,
    치료비 1201-01-23456 계좌로 보내주세요!
    """

    result = check_scam_in_message(text)

    print(f"\n[OK] 신고 여부: {result['has_reported_identifier']}")
    print(f"[PHONE] 추출된 전화번호: {result['extracted_identifiers']['phones']}")
    print(f"[ACCOUNT] 추출된 계좌번호: {result['extracted_identifiers']['accounts']}")

    print(f"\n[ALERT] 신고된 전화번호 ({len(result['reported_phones'])}건)")
    for phone in result['reported_phones']:
        print(f"   - {phone['phone_number']} (출처: {phone.get('source', 'MockDB')})")

    print(f"\n[ALERT] 신고된 계좌번호 ({len(result['reported_accounts'])}건)")
    for account in result['reported_accounts']:
        print(f"   - {account['account_number']} (출처: {account.get('source', 'MockDB')})")

    print(f"\n[WARN] 최대 위험 점수: {result['max_risk_score']}")
    print(f"[ACTION] 권장 조치: {result['recommended_action']}")

def test_api_availability():
    """TheCheat API 사용 가능 여부 확인"""
    print("\n" + "="*50)
    print("테스트 0: TheCheat API 연결 확인")
    print("="*50)

    from core.thecheat_api import get_thecheat_client
    import os

    api_key = os.getenv("THECHEAT_API_KEY")
    print(f"\n[KEY] THECHEAT_API_KEY 설정: {'있음' if api_key else '없음'}")

    client = get_thecheat_client()
    if client:
        print("[OK] TheCheat API 클라이언트 초기화 성공")
        print(f"[API] API URL: {client.base_url}")
    else:
        print("[WARN] TheCheat API 사용 불가 (Mock DB만 사용)")
        print("       .env 파일에 THECHEAT_API_KEY를 설정해주세요.")

if __name__ == "__main__":
    print("\n" + "=== TheCheat API Integration Test ===" + "\n")

    try:
        test_api_availability()
        test_phone_check()
        test_account_check()
        test_combined()

        print("\n" + "="*50)
        print("[OK] 모든 테스트 완료!")
        print("="*50)

    except Exception as e:
        print(f"\n[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
