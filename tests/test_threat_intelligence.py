"""
Threat Intelligence API 통합 테스트

테스트 항목:
1. lrl.kr URL 안전검사 API
2. VirusTotal URL 분석 API
3. TheCheat 계좌/전화번호 조회 (기존)
4. KISA 피싱사이트 캐시 (기존)
5. ThreatIntelligence 통합 모듈
6. threat_intelligence_mcp MCP 도구

실행 방법:
    cd D:\Data\18_KAT\KAT
    python -m pytest tests/test_threat_intelligence.py -v

    또는 직접 실행:
    python tests/test_threat_intelligence.py
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from unittest.mock import patch, MagicMock


# ============================================================
# 1. lrl.kr API 테스트
# ============================================================

class TestLRLAPI:
    """lrl.kr URL 안전검사 API 테스트"""

    def test_import(self):
        """모듈 import 테스트"""
        try:
            from agent.core.lrl_api import LRLClient, check_url_lrl, LRLAPIError
            assert LRLClient is not None
            assert check_url_lrl is not None
            print("[PASS] lrl_api 모듈 import 성공")
        except ImportError as e:
            pytest.skip(f"lrl_api 모듈 없음: {e}")

    def test_check_safe_url(self):
        """안전한 URL 테스트 (Mock)"""
        try:
            from agent.core.lrl_api import LRLClient
        except ImportError:
            pytest.skip("lrl_api 모듈 없음")

        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "result": {"safe": "1", "threat": ""},
                "message": "SUCCESS"
            }

            client = LRLClient(api_key="test_key")
            result = client.check_url("https://www.google.com")

            assert result["is_safe"] == True
            print(f"[PASS] 안전한 URL 테스트: {result}")

    def test_check_dangerous_url(self):
        """위험한 URL 테스트 (Mock)"""
        try:
            from agent.core.lrl_api import LRLClient
        except ImportError:
            pytest.skip("lrl_api 모듈 없음")

        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "result": {"safe": "0", "threat": "SOCIAL_ENGINEERING"},
                "message": "SUCCESS"
            }

            client = LRLClient(api_key="test_key")
            result = client.check_url("https://phishing-site.com")

            assert result["is_safe"] == False
            assert result["threat"] == "SOCIAL_ENGINEERING"
            print(f"[PASS] 위험한 URL 테스트: {result}")


# ============================================================
# 2. VirusTotal API 테스트
# ============================================================

class TestVirusTotalAPI:
    """VirusTotal URL 분석 API 테스트"""

    def test_import(self):
        """모듈 import 테스트"""
        try:
            from agent.core.virustotal_api import VirusTotalClient, check_url_virustotal
            assert VirusTotalClient is not None
            print("[PASS] virustotal_api 모듈 import 성공")
        except ImportError as e:
            pytest.skip(f"virustotal_api 모듈 없음: {e}")

    def test_url_id_generation(self):
        """URL ID 생성 테스트"""
        try:
            from agent.core.virustotal_api import VirusTotalClient
        except ImportError:
            pytest.skip("virustotal_api 모듈 없음")

        client = VirusTotalClient(api_key="test_key")
        url_id = client._get_url_id("https://www.google.com")

        assert url_id is not None
        assert len(url_id) > 0
        print(f"[PASS] URL ID 생성: {url_id}")

    def test_check_url_mock(self):
        """URL 분석 테스트 (Mock)"""
        try:
            from agent.core.virustotal_api import VirusTotalClient
        except ImportError:
            pytest.skip("virustotal_api 모듈 없음")

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 0,
                            "suspicious": 0,
                            "harmless": 70,
                            "undetected": 10
                        }
                    }
                }
            }

            client = VirusTotalClient(api_key="test_key")
            result = client.check_url("https://www.google.com")

            assert result["malicious"] == 0
            print(f"[PASS] VirusTotal URL 분석: {result}")


# ============================================================
# 3. TheCheat API 테스트 (기존)
# ============================================================

class TestTheCheatAPI:
    """TheCheat 계좌/전화번호 조회 테스트"""

    def test_import(self):
        """모듈 import 테스트"""
        from agent.core.thecheat_api import TheCheatClient, check_phone_thecheat
        assert TheCheatClient is not None
        print("[PASS] thecheat_api 모듈 import 성공")

    def test_normalize_phone(self):
        """전화번호 정규화 테스트"""
        from agent.core.thecheat_api import TheCheatClient

        client = TheCheatClient.__new__(TheCheatClient)
        client.api_key = "test"

        assert client._normalize_phone("010-1234-5678") == "01012345678"
        assert client._normalize_phone("010 1234 5678") == "01012345678"
        print("[PASS] 전화번호 정규화 테스트")


# ============================================================
# 4. KISA 피싱사이트 캐시 테스트 (기존)
# ============================================================

class TestKISAPhishing:
    """KISA 피싱사이트 캐시 테스트"""

    def test_import(self):
        """모듈 import 테스트"""
        from agent.core.kisa_phishing_api import KISAPhishingCache, check_url_kisa
        assert KISAPhishingCache is not None
        print("[PASS] kisa_phishing_api 모듈 import 성공")

    def test_domain_extraction(self):
        """도메인 추출 테스트"""
        from agent.core.kisa_phishing_api import KISAPhishingCache

        cache = KISAPhishingCache.__new__(KISAPhishingCache)

        assert cache._extract_domain("http://www.example.com/path") == "example.com"
        assert cache._extract_domain("https://EXAMPLE.COM") == "example.com"
        assert cache._extract_domain("example.com") == "example.com"
        print("[PASS] 도메인 추출 테스트")


# ============================================================
# 5. ThreatIntelligence 통합 모듈 테스트
# ============================================================

class TestThreatIntelligence:
    """통합 위협 정보 조회 테스트"""

    def test_import(self):
        """모듈 import 테스트"""
        try:
            from agent.core.threat_intelligence import ThreatIntelligence, calculate_prior_probability
            assert ThreatIntelligence is not None
            print("[PASS] threat_intelligence 모듈 import 성공")
        except ImportError as e:
            pytest.skip(f"threat_intelligence 모듈 없음: {e}")

    def test_prior_probability(self):
        """사전 확률 계산 테스트"""
        try:
            from agent.core.threat_intelligence import calculate_prior_probability
        except ImportError:
            pytest.skip("threat_intelligence 모듈 없음")

        # report_count / (report_count + 100)
        assert calculate_prior_probability(0) == 0.0
        assert calculate_prior_probability(100) == 0.5
        assert abs(calculate_prior_probability(342) - 0.774) < 0.01  # 342/(342+100) ≈ 0.774
        print("[PASS] 사전 확률 계산 테스트")

    def test_check_identifier_phone(self):
        """전화번호 통합 조회 테스트"""
        try:
            from agent.core.threat_intelligence import ThreatIntelligence
        except ImportError:
            pytest.skip("threat_intelligence 모듈 없음")

        ti = ThreatIntelligence()

        with patch.object(ti, 'check_phone') as mock_check:
            mock_check.return_value = {
                "has_reported": True,
                "source": "TheCheat",
                "report_count": 5,
                "prior_probability": 0.048
            }

            result = ti.check_identifier("010-1234-5678", "phone")
            assert result["has_reported"] == True
            print(f"[PASS] 전화번호 통합 조회: {result}")

    def test_check_identifier_url(self):
        """URL 통합 조회 테스트"""
        try:
            from agent.core.threat_intelligence import ThreatIntelligence
        except ImportError:
            pytest.skip("threat_intelligence 모듈 없음")

        ti = ThreatIntelligence()

        with patch.object(ti, 'check_url') as mock_check:
            mock_check.return_value = {
                "has_reported": True,
                "source": "lrl.kr",
                "threat_type": "SOCIAL_ENGINEERING",
                "prior_probability": 0.95
            }

            result = ti.check_identifier("https://phishing.com", "url")
            assert result["has_reported"] == True
            print(f"[PASS] URL 통합 조회: {result}")


# ============================================================
# 6. MCP 도구 테스트
# ============================================================

class TestMCPTool:
    """threat_intelligence_mcp MCP 도구 테스트"""

    def test_import(self):
        """MCP 도구 import 테스트"""
        try:
            from agent.mcp.tools import threat_intelligence_mcp
            assert threat_intelligence_mcp is not None
            print("[PASS] threat_intelligence_mcp 도구 import 성공")
        except (ImportError, AttributeError) as e:
            pytest.skip(f"threat_intelligence_mcp 도구 없음: {e}")


# ============================================================
# 7. 메트릭 테스트
# ============================================================

class TestMetrics:
    """Threat Intelligence 메트릭 테스트"""

    def test_import(self):
        """메트릭 import 테스트"""
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "ops" / "monitoring"))
            from metrics.kat_metrics import KATMetrics

            metrics = KATMetrics()
            assert hasattr(metrics, 'threat_intel_queries')
            assert hasattr(metrics, 'threat_intel_hits')
            assert hasattr(metrics, 'threat_intel_duration')
            print("[PASS] Threat Intelligence 메트릭 존재 확인")
        except (ImportError, AttributeError) as e:
            pytest.skip(f"메트릭 없음: {e}")

    def test_record_query(self):
        """메트릭 기록 테스트"""
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "ops" / "monitoring"))
            from metrics.kat_metrics import KATMetrics

            metrics = KATMetrics()
            metrics.record_threat_intel_query("lrl", "url", hit=True)
            print("[PASS] 메트릭 기록 테스트")
        except (ImportError, AttributeError) as e:
            pytest.skip(f"메트릭 메서드 없음: {e}")


# ============================================================
# 직접 실행
# ============================================================

def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("Threat Intelligence API 통합 테스트")
    print("=" * 60)

    test_classes = [
        TestLRLAPI,
        TestVirusTotalAPI,
        TestTheCheatAPI,
        TestKISAPhishing,
        TestThreatIntelligence,
        TestMCPTool,
        TestMetrics
    ]

    results = {"passed": 0, "failed": 0, "skipped": 0}

    for test_class in test_classes:
        print(f"\n--- {test_class.__name__} ---")
        instance = test_class()

        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    method = getattr(instance, method_name)
                    method()
                    results["passed"] += 1
                except pytest.skip.Exception as e:
                    print(f"[SKIP] {method_name}: {e}")
                    results["skipped"] += 1
                except Exception as e:
                    print(f"[FAIL] {method_name}: {e}")
                    results["failed"] += 1

    print("\n" + "=" * 60)
    print(f"결과: PASSED={results['passed']}, FAILED={results['failed']}, SKIPPED={results['skipped']}")
    print("=" * 60)

    return results["failed"] == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
