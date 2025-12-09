"""
Threat Intelligence API 실제 호출 테스트

이 스크립트는 실제 API를 호출하여 연동 상태를 확인합니다.
API 키가 설정되지 않은 경우 해당 테스트는 SKIP 됩니다.

환경변수 설정 필요:
    - LRL_API_KEY: lrl.kr URL 안전검사 API
    - VIRUSTOTAL_API_KEY: VirusTotal API
    - THECHEAT_API_KEY: 더치트 API
    - KISA_PHISHING_API_KEY: KISA 피싱사이트 API

실행 방법:
    cd D:\\Data\\18_KAT\\KAT
    python tests/test_api_live.py

    또는 특정 API만:
    python tests/test_api_live.py --api lrl
    python tests/test_api_live.py --api virustotal
    python tests/test_api_live.py --api thecheat
    python tests/test_api_live.py --api kisa
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# dotenv 로드
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(name: str, success: bool, details: dict = None):
    status = "[PASS]" if success else "[FAIL]"
    print(f"\n{status} {name}")
    if details:
        for key, value in details.items():
            print(f"    {key}: {value}")


# ============================================================
# 1. lrl.kr API 테스트
# ============================================================

def test_lrl_api():
    """lrl.kr URL 안전검사 API 실제 호출 테스트"""
    print_header("lrl.kr URL 안전검사 API")

    api_key = os.getenv("LRL_API_KEY")
    if not api_key:
        print("[SKIP] LRL_API_KEY 환경변수가 설정되지 않았습니다.")
        print("       https://api.lrl.kr 에서 API 키를 발급받으세요.")
        return None

    try:
        from agent.core.lrl_api import LRLClient
        client = LRLClient(api_key=api_key)

        # 테스트 1: 안전한 URL
        print("\n[TEST 1] 안전한 URL (google.com)")
        result = client.check_url("https://www.google.com")
        print_result("google.com", result.get("is_safe", False), result)

        # 테스트 2: 의심 URL (테스트용)
        print("\n[TEST 2] 일반 URL (naver.com)")
        result = client.check_url("https://www.naver.com")
        print_result("naver.com", result.get("is_safe", False), result)

        return True

    except Exception as e:
        print(f"[ERROR] API 호출 실패: {e}")
        return False


# ============================================================
# 2. VirusTotal API 테스트
# ============================================================

def test_virustotal_api():
    """VirusTotal API 실제 호출 테스트"""
    print_header("VirusTotal API")

    api_key = os.getenv("VIRUSTOTAL_API_KEY")
    if not api_key:
        print("[SKIP] VIRUSTOTAL_API_KEY 환경변수가 설정되지 않았습니다.")
        print("       https://www.virustotal.com 에서 무료 계정 가입 후 API 키를 발급받으세요.")
        return None

    try:
        from agent.core.virustotal_api import VirusTotalClient
        client = VirusTotalClient(api_key=api_key)

        # 테스트: 안전한 URL
        print("\n[TEST] 안전한 URL (google.com)")
        print("       (Rate limit: 15초 대기 필요)")
        result = client.check_url("https://www.google.com")

        is_safe = result.get("malicious", 0) == 0
        print_result("google.com", is_safe, {
            "malicious": result.get("malicious"),
            "suspicious": result.get("suspicious"),
            "harmless": result.get("harmless"),
            "total_engines": result.get("total_engines")
        })

        return True

    except Exception as e:
        print(f"[ERROR] API 호출 실패: {e}")
        return False


# ============================================================
# 3. TheCheat API 테스트
# ============================================================

def test_thecheat_api():
    """TheCheat 사기조회 API 실제 호출 테스트"""
    print_header("TheCheat 사기조회 API")

    api_key = os.getenv("THECHEAT_API_KEY")
    if not api_key:
        print("[SKIP] THECHEAT_API_KEY 환경변수가 설정되지 않았습니다.")
        print("       https://thecheat.co.kr 에서 API 키를 발급받으세요.")
        return None

    try:
        from agent.core.thecheat_api import TheCheatClient
        client = TheCheatClient(api_key=api_key)

        # 테스트: 임의의 전화번호 (신고 없을 것으로 예상)
        print("\n[TEST 1] 전화번호 조회 (010-0000-0000)")
        result = client.search_phone("010-0000-0000")
        print_result("전화번호 조회", True, {
            "is_reported": result.get("is_reported"),
            "caution": result.get("caution"),
            "source": result.get("source")
        })

        # 테스트: 임의의 계좌번호
        print("\n[TEST 2] 계좌번호 조회 (000-00-000000)")
        result = client.search_account("000-00-000000")
        print_result("계좌번호 조회", True, {
            "is_reported": result.get("is_reported"),
            "caution": result.get("caution"),
            "source": result.get("source")
        })

        return True

    except Exception as e:
        print(f"[ERROR] API 호출 실패: {e}")
        return False


# ============================================================
# 4. KISA 피싱사이트 API 테스트
# ============================================================

def test_kisa_api():
    """KISA 피싱사이트 API 실제 호출 테스트"""
    print_header("KISA 피싱사이트 API")

    api_key = os.getenv("KISA_PHISHING_API_KEY")
    if not api_key or api_key == "your_kisa_api_key_here":
        print("[SKIP] KISA_PHISHING_API_KEY 환경변수가 설정되지 않았습니다.")
        print("       https://www.data.go.kr 에서 KISA 피싱사이트 Open API 키를 발급받으세요.")
        return None

    try:
        from agent.core.kisa_phishing_api import KISAPhishingClient, KISAPhishingCache

        # 테스트 1: API 연결
        print("\n[TEST 1] API 연결 테스트 (첫 페이지 조회)")
        client = KISAPhishingClient(api_key=api_key)
        result = client.fetch_page(page=1, per_page=10)

        print_result("API 연결", True, {
            "total_count": result.get("totalCount"),
            "current_page_count": result.get("currentCount"),
            "sample_url": result.get("data", [{}])[0].get("홈페이지주소", "N/A")
        })

        # 테스트 2: 캐시 상태
        print("\n[TEST 2] 로컬 캐시 상태")
        cache = KISAPhishingCache()
        print_result("캐시 상태", True, {
            "total_cached": cache.cache_data.get("total_count", 0),
            "updated_at": cache.cache_data.get("updated_at", "Never"),
            "is_expired": cache.is_expired()
        })

        return True

    except Exception as e:
        print(f"[ERROR] API 호출 실패: {e}")
        return False


# ============================================================
# 5. 통합 ThreatIntelligence 테스트
# ============================================================

def test_threat_intelligence():
    """ThreatIntelligence 통합 모듈 테스트"""
    print_header("ThreatIntelligence 통합 모듈")

    try:
        from agent.core.threat_intelligence import ThreatIntelligence, calculate_prior_probability

        ti = ThreatIntelligence()

        # 테스트 1: Prior 확률 계산
        print("\n[TEST 1] Prior 확률 계산")
        test_cases = [0, 1, 10, 100, 342, 1000]
        for count in test_cases:
            prob = calculate_prior_probability(count)
            print(f"    report_count={count} → prior_probability={prob:.4f}")

        # 테스트 2: URL 통합 조회 (API 키 있는 것만 사용)
        print("\n[TEST 2] URL 통합 조회")
        result = ti.check_url("https://www.google.com")
        print_result("URL 조회", True, {
            "has_reported": result.get("has_reported"),
            "source": result.get("source"),
            "threat_type": result.get("threat_type")
        })

        # 테스트 3: 전화번호 통합 조회
        print("\n[TEST 3] 전화번호 통합 조회")
        result = ti.check_phone("010-0000-0000")
        print_result("전화번호 조회", True, {
            "has_reported": result.get("has_reported"),
            "source": result.get("source"),
            "prior_probability": result.get("prior_probability")
        })

        return True

    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# 메인
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Threat Intelligence API 실제 호출 테스트")
    parser.add_argument("--api", choices=["lrl", "virustotal", "thecheat", "kisa", "all", "integrated"],
                       default="all", help="테스트할 API 선택")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  Threat Intelligence API 실제 호출 테스트")
    print(f"  실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 환경변수 현황
    print("\n[환경변수 현황]")
    env_vars = {
        "LRL_API_KEY": os.getenv("LRL_API_KEY"),
        "VIRUSTOTAL_API_KEY": os.getenv("VIRUSTOTAL_API_KEY"),
        "THECHEAT_API_KEY": os.getenv("THECHEAT_API_KEY"),
        "KISA_PHISHING_API_KEY": os.getenv("KISA_PHISHING_API_KEY")
    }
    for name, value in env_vars.items():
        status = "설정됨" if value else "미설정"
        masked = f"{value[:8]}..." if value and len(value) > 8 else value
        print(f"    {name}: {status} {f'({masked})' if value else ''}")

    results = {}

    # 테스트 실행
    if args.api in ["lrl", "all"]:
        results["lrl"] = test_lrl_api()

    if args.api in ["virustotal", "all"]:
        results["virustotal"] = test_virustotal_api()

    if args.api in ["thecheat", "all"]:
        results["thecheat"] = test_thecheat_api()

    if args.api in ["kisa", "all"]:
        results["kisa"] = test_kisa_api()

    if args.api in ["integrated", "all"]:
        results["integrated"] = test_threat_intelligence()

    # 결과 요약
    print_header("테스트 결과 요약")
    for api, result in results.items():
        if result is None:
            status = "SKIP (API 키 없음)"
        elif result:
            status = "PASS"
        else:
            status = "FAIL"
        print(f"    {api}: {status}")

    # 실패한 테스트가 있으면 exit code 1
    failures = [k for k, v in results.items() if v is False]
    if failures:
        print(f"\n[!] 실패한 테스트: {', '.join(failures)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
