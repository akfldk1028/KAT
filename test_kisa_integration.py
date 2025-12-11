"""
KISA 피싱사이트 URL API 통합 테스트 스크립트

테스트 시나리오:
1. API Key 설정 확인
2. 로컬 캐시 생성 (첫 실행)
3. URL 감지 및 KISA DB 조회
4. TheCheat API와 함께 동작 확인

실행 방법:
1. .env 파일에 KISA_PHISHING_API_KEY 설정
2. python test_kisa_integration.py
"""

import sys
from pathlib import Path

# agent 모듈 경로 추가
agent_path = Path(__file__).parent / "agent"
sys.path.insert(0, str(agent_path))

from dotenv import load_dotenv
load_dotenv()

import os
from core.kisa_phishing_api import KISAPhishingClient, KISAPhishingCache, check_url_kisa
from core.threat_matcher import detect_urls

def test_api_availability():
    """KISA API 사용 가능 여부 확인"""
    print("\n" + "="*60)
    print("테스트 0: KISA API 연결 확인")
    print("="*60)

    api_key = os.getenv("KISA_PHISHING_API_KEY")
    print(f"\n[KEY] KISA_PHISHING_API_KEY 설정: {'있음' if api_key and api_key != 'your_kisa_api_key_here' else '없음'}")

    if not api_key or api_key == "your_kisa_api_key_here":
        print("[WARN] KISA API 사용 불가 (캐시만 사용)")
        print("       .env 파일에 KISA_PHISHING_API_KEY를 설정해주세요.")
        print("\n[LINK] API Key 발급: https://www.data.go.kr/data/15109780/fileData.do")
        return False

    try:
        client = KISAPhishingClient(api_key=api_key)
        print("[OK] KISA API 클라이언트 초기화 성공")
        print(f"[API] API URL: {client.endpoint}")

        # 첫 페이지 조회 테스트
        result = client.fetch_page(page=1, per_page=10)
        print(f"[OK] API 호출 성공: {result['totalCount']} 개 레코드 확인")
        return True

    except Exception as e:
        print(f"[ERROR] KISA API 호출 실패: {e}")
        return False


def test_cache_creation():
    """로컬 캐시 생성 테스트"""
    print("\n" + "="*60)
    print("테스트 1: 로컬 캐시 생성")
    print("="*60)

    api_key = os.getenv("KISA_PHISHING_API_KEY")
    if not api_key or api_key == "your_kisa_api_key_here":
        print("[SKIP] API Key 없음 - 캐시 생성 생략")
        return

    try:
        cache = KISAPhishingCache()

        # 캐시 만료 확인
        if cache.is_expired(ttl=86400):
            print("[INFO] 캐시 만료됨 - 업데이트 시작...")
            print("[WAIT] KISA DB 다운로드 중 (~30초 소요)...")

            client = KISAPhishingClient(api_key=api_key)
            cache.update_cache(client)

            print(f"[OK] 캐시 업데이트 완료")
            print(f"[INFO] 총 {cache.cache_data['total_count']} 개 레코드")
            print(f"[INFO] 도메인 인덱스: {len(cache.cache_data['domain_index'])} 개")
        else:
            print("[OK] 캐시 유효함 - 업데이트 불필요")
            print(f"[INFO] 총 {cache.cache_data['total_count']} 개 레코드")
            print(f"[INFO] 마지막 업데이트: {cache.cache_data['updated_at']}")

    except Exception as e:
        print(f"[ERROR] 캐시 생성 실패: {e}")
        import traceback
        traceback.print_exc()


def test_url_detection():
    """URL 감지 및 KISA 조회 테스트"""
    print("\n" + "="*60)
    print("테스트 2: URL 감지 및 KISA 조회")
    print("="*60)

    # 테스트 케이스 1: 정상 URL
    print("\n[테스트 2-1] 정상 URL (Google)")
    text1 = "여기 들어가세요: https://www.google.com"
    result1 = detect_urls(text1)

    print(f"[URL] 발견된 URL: {result1['urls_found']}")
    print(f"[SAFE] 안전한 URL: {result1['safe_urls']}")
    print(f"[SUSP] 의심스러운 URL: {result1['suspicious_urls']}")
    print(f"[KISA] 피싱 URL: {result1.get('kisa_phishing_urls', [])}")
    print(f"[COUNT] 피싱 개수: {result1.get('phishing_count', 0)}")

    # 테스트 케이스 2: 의심스러운 URL (가상의 도메인)
    print("\n[테스트 2-2] 의심스러운 URL")
    text2 = "긴급! 여기서 로그인: http://suspicious-phishing-test.com"
    result2 = detect_urls(text2)

    print(f"[URL] 발견된 URL: {result2['urls_found']}")
    print(f"[SAFE] 안전한 URL: {result2['safe_urls']}")
    print(f"[SUSP] 의심스러운 URL: {result2['suspicious_urls']}")
    print(f"[KISA] 피싱 URL: {result2.get('kisa_phishing_urls', [])}")
    print(f"[COUNT] 피싱 개수: {result2.get('phishing_count', 0)}")

    # 테스트 케이스 3: 단축 URL
    print("\n[테스트 2-3] 단축 URL (bit.ly)")
    text3 = "[택배] 주소 확인: bit.ly/test123"
    result3 = detect_urls(text3)

    print(f"[URL] 발견된 URL: {result3['urls_found']}")
    print(f"[SHORT] 단축 URL 포함: {result3['has_shortened_url']}")
    print(f"[SUSP] 의심스러운 URL: {result3['suspicious_urls']}")
    print(f"[KISA] 피싱 URL: {result3.get('kisa_phishing_urls', [])}")


def test_cache_lookup():
    """캐시 직접 조회 테스트"""
    print("\n" + "="*60)
    print("테스트 3: 캐시 직접 조회")
    print("="*60)

    cache = KISAPhishingCache()

    # 샘플 URL로 캐시 조회
    test_urls = [
        "http://google.com",
        "http://naver.com",
        "http://phishing-example.com"
    ]

    for url in test_urls:
        result = cache.is_phishing(url)
        if result:
            print(f"\n[ALERT] {url}")
            print(f"   - 피싱사이트로 등록됨")
            print(f"   - 신고일: {result['reported_date']}")
        else:
            print(f"\n[OK] {url}")
            print(f"   - KISA DB에 없음 (안전 추정)")


def test_wrapper_function():
    """Wrapper 함수 테스트 (check_url_kisa)"""
    print("\n" + "="*60)
    print("테스트 4: Wrapper 함수 테스트")
    print("="*60)

    test_urls = [
        "http://google.com",
        "http://suspicious-domain.com",
        "http://bit.ly/test123"
    ]

    for url in test_urls:
        result = check_url_kisa(url)
        print(f"\n[URL] {url}")
        if result:
            print(f"   [ALERT] 피싱사이트 발견!")
            print(f"   - matched_url: {result['matched_url']}")
            print(f"   - reported_date: {result['reported_date']}")
            print(f"   - source: {result['source']}")
        else:
            print(f"   [OK] 안전 (DB에 없음 또는 API Key 미설정)")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("=== KISA 피싱사이트 URL API 통합 테스트 ===")
    print("="*60)

    try:
        # API 사용 가능 여부 확인
        api_available = test_api_availability()

        # 캐시 생성 (API Key 있을 때만)
        if api_available:
            test_cache_creation()

        # URL 감지 테스트
        test_url_detection()

        # 캐시 직접 조회 테스트
        test_cache_lookup()

        # Wrapper 함수 테스트
        test_wrapper_function()

        print("\n" + "="*60)
        print("[OK] 모든 테스트 완료!")
        print("="*60)

        if not api_available:
            print("\n[INFO] KISA API를 사용하려면:")
            print("   1. https://www.data.go.kr/data/15109780/fileData.do 에서 API Key 발급")
            print("   2. .env 파일에 KISA_PHISHING_API_KEY 설정")
            print("   3. 다시 테스트 실행")

    except Exception as e:
        print(f"\n[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
